"""Detalhe/status da análise e correções SEI — extraído de `api/analysis.py`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis_filters import _filter_corrections
from app.api.analysis_scoring import estimate_tokens
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.schemas.analysis import (
    AnalysisDetailResponse,
    Art6ChecklistItem,
    CorrectionResponse,
)
from app.services.analyzer.art6_status import build_art6_checklist, summarize_art6_coverage

router = APIRouter(prefix="/analysis", tags=["Análise"])


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Status da análise",
    description="Retorna o status e resultados parciais/completos de uma análise.",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    for_sei: bool = False,
    review_status: str | None = None,
    severity_min: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes da análise com correções (filtro opcional para SEI)."""
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

    resp = AnalysisDetailResponse.model_validate(analysis)
    statuses = (
        {s.strip() for s in review_status.split(",") if s.strip()}
        if review_status
        else None
    )
    filtered = _filter_corrections(
        analysis.corrections,
        for_sei=for_sei,
        review_statuses=statuses,
        severity_min=severity_min,
    )
    if for_sei or statuses is not None or severity_min is not None:
        resp.corrections = [CorrectionResponse.model_validate(c) for c in filtered]
    resp.tokens_estimated = estimate_tokens(analysis)
    items = list(analysis.document.items or []) if analysis.document else []
    checklist_rows = build_art6_checklist(items, analysis.corrections)
    resp.art6_checklist = [Art6ChecklistItem(**row) for row in checklist_rows]
    summary = summarize_art6_coverage(checklist_rows)
    resp.art6_coverage = summary["art6_coverage"]
    resp.art6_meets_target = summary["art6_meets_target"]

    snapshot = analysis.run_snapshot or {}
    raw_ids = snapshot.get("analyzed_item_ids") or []
    parsed_ids: list[uuid.UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(uuid.UUID(str(raw)))
        except (ValueError, TypeError):
            continue
    resp.analyzed_item_ids = parsed_ids
    resp.budget_truncated = bool(snapshot.get("budget_truncated"))
    if not resp.budget_truncated and analysis.error_message:
        msg = analysis.error_message
        resp.budget_truncated = (
            "ANALYSIS_MAX_LLM_CALLS" in msg
            or "itens prioritários" in msg
        )
    return resp


@router.get(
    "/{analysis_id}/sei-corrections",
    response_model=list[CorrectionResponse],
    summary="Correções aplicáveis ao SEI",
    description="Somente correções com review_status aprovada ou ajustada.",
)
async def get_sei_corrections(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    return [CorrectionResponse.model_validate(c) for c in filtered]


@router.get(
    "/document/{document_id}",
    response_model=list[AnalysisDetailResponse],
    summary="Análises de um documento",
    description="Retorna todas as análises realizadas sobre um documento.",
)
async def list_document_analyses(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista análises de um documento."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.document_id == document_id)
        .order_by(Analysis.created_at.desc())
    )
    analyses = result.scalars().all()

    out: list[AnalysisDetailResponse] = []
    for a in analyses:
        resp = AnalysisDetailResponse.model_validate(a)
        resp.tokens_estimated = estimate_tokens(a)
        snapshot = a.run_snapshot or {}
        raw_ids = snapshot.get("analyzed_item_ids") or []
        parsed: list[uuid.UUID] = []
        for raw in raw_ids:
            try:
                parsed.append(uuid.UUID(str(raw)))
            except (ValueError, TypeError):
                continue
        resp.analyzed_item_ids = parsed
        resp.budget_truncated = bool(snapshot.get("budget_truncated"))
        out.append(resp)
    return out
