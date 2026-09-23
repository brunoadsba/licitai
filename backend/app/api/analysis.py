"""
Endpoints para iniciar análises de documentos.
Detalhe/revisão/exports/relatório vivem em módulos próprios
(`analysis_details`, `analysis_review`, `sei_exports`, `analysis_report`).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document, DocumentItem
from app.schemas.analysis import (
    AnalysisStartRequest,
    AnalysisStartResponse,
)
from app.services.jobs import enqueue
from app.services.privacy import (
    CloudPrivacyError,
    assert_cloud_allowed_for_document,
    resolve_classification,
)
from app.utils import idempotency as idempotency_cache
from app.utils.request_context import request_id_var

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Análise"])

PROMPT_VERSION = "v1"


async def _build_analysis_snapshot(
    db: AsyncSession, document: Document
) -> dict:
    items = (
        await db.execute(
            select(DocumentItem.id).where(
                DocumentItem.document_id == document.id,
                DocumentItem.archived_at.is_(None),
            )
        )
    ).scalars().all()
    return {
        "item_ids": [str(i) for i in items],
        "prompt_version": PROMPT_VERSION,
        "corpus_version": "legal-v2",
        "provider": settings.llm_provider,
        "model": _get_current_model(),
        "analysis_mode": None,  # preenchido pelo caller
    }


@router.post(
    "/{document_id}/start",
    response_model=AnalysisStartResponse,
    status_code=202,
    summary="Iniciar análise",
    description="Inicia a análise completa de um documento usando IA.",
)
async def start_analysis(
    document_id: uuid.UUID,
    payload: AnalysisStartRequest | None = None,
    x_document_classification: str | None = Header(
        default=None, alias="X-Document-Classification"
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Enfileira análise na fila durável (processada por `python -m app.worker`)."""
    mode = payload.mode if payload and payload.mode else "economic"
    if idempotency_key:
        cached = idempotency_cache.lookup(f"analysis:{document_id}:{idempotency_key}")
        if cached:
            logger.info(
                "analysis.start.idempotent_hit doc=%s request_id=%s",
                document_id, request_id_var.get(),
            )
            return AnalysisStartResponse(**cached)
    if mode not in ("multi_agent", "single", "economic"):
        raise HTTPException(
            status_code=422,
            detail="mode inválido. Use: multi_agent, single ou economic.",
        )

    result = await db.execute(
        select(Document).where(Document.id == document_id).with_for_update()
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    if getattr(document, "document_type", "tr") != "tr":
        raise HTTPException(
            status_code=400,
            detail="Somente Termos de Referência podem ser analisados. Propostas usam Comparações.",
        )

    classification = resolve_classification(
        header_value=x_document_classification,
        document_classification=getattr(document, "classification", None),
    )
    try:
        assert_cloud_allowed_for_document(classification)
    except CloudPrivacyError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    if document.status not in ("parsed", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Documento não está pronto para análise. Status atual: {document.status}",
        )

    running = await db.execute(
        select(Analysis).where(
            Analysis.document_id == document_id,
            Analysis.status.in_(["pending", "running"]),
        )
    )
    existing_analysis = running.scalar_one_or_none()
    if existing_analysis:
        if existing_analysis.status == "pending":
            logger.info(
                "Re-enfileirando análise pendente %s (doc %s)",
                existing_analysis.id, document_id,
            )
            job = await enqueue(
                db,
                "analysis",
                {
                    "analysis_id": str(existing_analysis.id),
                    "document_id": str(document_id),
                },
            )
            await db.commit()
            return AnalysisStartResponse(
                analysis_id=existing_analysis.id,
                job_id=job.id,
                message=(
                    "Análise pendente re-enfileirada. "
                    "Requer worker (`python -m app.worker`)."
                ),
            )
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        )

    snapshot = await _build_analysis_snapshot(db, document)
    snapshot["analysis_mode"] = mode

    analysis = Analysis(
        document_id=document_id,
        status="pending",
        llm_provider=settings.llm_provider,
        llm_model=_get_current_model(),
        analysis_mode=mode,
        total_items=document.total_items,
        run_snapshot=snapshot,
    )
    db.add(analysis)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma análise em andamento para este documento.",
        ) from exc

    analysis_id = analysis.id
    job = await enqueue(
        db,
        "analysis",
        {"analysis_id": str(analysis_id), "document_id": str(document_id)},
    )
    await db.commit()

    logger.info(
        "Análise %s enfileirada job=%s (doc %s) request_id=%s",
        analysis_id, job.id, document_id, request_id_var.get(),
    )

    resp = AnalysisStartResponse(
        analysis_id=analysis_id,
        job_id=job.id,
        message=(
            "Análise enfileirada. Acompanhe pelo status "
            "(worker: `python -m app.worker`)."
        ),
    )
    if idempotency_key:
        idempotency_cache.store(
            f"analysis:{document_id}:{idempotency_key}",
            {"analysis_id": analysis_id, "job_id": job.id, "message": resp.message},
        )
    return resp


def _get_current_model() -> str:
    """Retorna o nome do modelo LLM configurado."""
    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return model_map.get(settings.llm_provider, "unknown")
