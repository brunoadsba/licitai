"""Reanálise parcial de itens — extraído de `api/analysis.py`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis import _build_analysis_snapshot, _get_current_model
from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.schemas.analysis import AnalysisStartResponse
from app.services.jobs import enqueue

router = APIRouter(prefix="/analysis", tags=["Análise"])


@router.post(
    "/{analysis_id}/reanalyze-partial",
    response_model=AnalysisStartResponse,
    status_code=202,
    summary="Reanalisar itens com cobertura incompleta",
)
async def reanalyze_partial(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Enfileira nova análise dos itens faltantes:
    - itens com coverage_errors na análise anterior; e/ou
    - cláusulas substantivas ainda não analisadas (orçamento truncado).
    """
    from app.services.parser.detection_substantive import is_substantive_content

    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    if analysis.status not in ("completed", "completed_with_errors", "error"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise atual concluir antes de reanalisar parcialmente.",
        )

    item_ids: set[str] = set()
    for c in analysis.corrections:
        evidence = getattr(c, "evidence", None) or {}
        if evidence.get("coverage_errors"):
            item_ids.add(str(c.document_item_id))

    snapshot_prev = analysis.run_snapshot or {}
    already = {str(x) for x in (snapshot_prev.get("analyzed_item_ids") or [])}
    for failed_id in snapshot_prev.get("failed_item_ids") or []:
        item_ids.add(str(failed_id))
    budget_cut = bool(snapshot_prev.get("budget_truncated"))
    if not budget_cut and analysis.error_message:
        budget_cut = (
            "ANALYSIS_MAX_LLM_CALLS" in analysis.error_message
            or "itens prioritários" in analysis.error_message
        )
    if budget_cut and analysis.document:
        for item in analysis.document.items:
            if getattr(item, "archived_at", None) is not None:
                continue
            sid = str(item.id)
            if sid in already:
                continue
            if is_substantive_content(
                item.content or "",
                item.title,
                item.item_number,
                item.item_type,
            ):
                item_ids.add(sid)

    if not item_ids:
        raise HTTPException(
            status_code=404,
            detail="Nenhum item pendente para reanalisar.",
        )

    doc_result = await db.execute(
        select(Document).where(Document.id == analysis.document_id).with_for_update()
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    running = await db.execute(
        select(Analysis).where(
            Analysis.document_id == document.id,
            Analysis.status.in_(["pending", "running"]),
        )
    )
    if running.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        )

    mode = analysis.analysis_mode or "economic"
    snapshot = await _build_analysis_snapshot(db, document)
    snapshot["analysis_mode"] = mode
    snapshot["only_item_ids"] = sorted(item_ids)

    new_analysis = Analysis(
        document_id=document.id,
        status="pending",
        llm_provider=settings.llm_provider,
        llm_model=_get_current_model(),
        analysis_mode=mode,
        total_items=len(item_ids),
        run_snapshot=snapshot,
    )
    db.add(new_analysis)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        ) from exc

    job = await enqueue(
        db,
        "analysis",
        {
            "analysis_id": str(new_analysis.id),
            "document_id": str(document.id),
        },
    )
    await db.commit()
    return AnalysisStartResponse(
        analysis_id=new_analysis.id,
        job_id=job.id,
        message=(
            f"Reanálise parcial enfileirada ({len(item_ids)} itens). "
            "Requer worker (`python -m app.worker`)."
        ),
    )
