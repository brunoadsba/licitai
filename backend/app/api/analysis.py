"""
Endpoints para análise de documentos e geração de relatórios.
"""

import logging
import uuid
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.schemas.analysis import (
    AnalysisDetailResponse,
    AnalysisStartRequest,
    AnalysisStartResponse,
    CorrectionResponse,
    CorrectionReviewUpdate,
    ReportResponse,
    ScoreDetail,
)
from app.services.jobs import enqueue
from app.services.privacy import (
    CloudPrivacyError,
    assert_cloud_allowed_for_document,
    resolve_classification,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Análise"])

PROMPT_VERSION = "v1"


def estimate_tokens(analysis: Analysis) -> int:
    base = (analysis.total_items or 0) * 900 + (analysis.analyzed_items or 0) * 100
    corr = len(getattr(analysis, "corrections", []) or [])
    return base + corr * 350 + 800


def _score_details(analysis: Analysis) -> list[ScoreDetail]:
    """Mapeia as notas da análise preservando zero legítimo (0.0 ≠ ausente)."""
    def _score(value) -> float | None:
        return float(value) if value is not None else None

    return [
        ScoreDetail(label="Nota Geral", score=_score(analysis.score_overall)),
        ScoreDetail(label="Segurança Jurídica", score=_score(analysis.score_juridical)),
        ScoreDetail(label="Qualidade Técnica", score=_score(analysis.score_technical)),
        ScoreDetail(label="Qualidade da Redação", score=_score(analysis.score_writing)),
        ScoreDetail(label="Conformidade Estrutural", score=_score(analysis.score_structural)),
    ]


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
        "corpus_version": "legal-v1",
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
    db: AsyncSession = Depends(get_db),
):
    """Enfileira análise na fila durável (processada por `python -m app.worker`)."""
    mode = payload.mode if payload and payload.mode else "multi_agent"

    result = await db.execute(
        select(Document).where(Document.id == document_id).with_for_update()
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    classification = resolve_classification(
        header_value=x_document_classification,
        document_classification=getattr(document, "classification", None),
    )
    try:
        assert_cloud_allowed_for_document(classification)
    except CloudPrivacyError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

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
        "Análise %s enfileirada job=%s (doc %s)", analysis_id, job.id, document_id
    )

    return AnalysisStartResponse(
        analysis_id=analysis_id,
        job_id=job.id,
        message=(
            "Análise enfileirada. Acompanhe pelo status "
            "(worker: `python -m app.worker`)."
        ),
    )


SEI_APPLICABLE_STATUSES = frozenset({"aprovada", "ajustada"})


@router.patch(
    "/corrections/{correction_id}",
    response_model=CorrectionResponse,
    summary="Revisão humana de correção",
    description=(
        "Atualiza review_status de uma correção (aprovada/rejeitada/ajustada/pendente). "
        "Somente aprovada e ajustada liberam cópia para o SEI."
    ),
)
async def update_correction_review(
    correction_id: uuid.UUID,
    payload: CorrectionReviewUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Aplica decisão humana de revisão em uma correção."""
    result = await db.execute(
        select(Correction).where(Correction.id == correction_id)
    )
    correction = result.scalar_one_or_none()
    if not correction:
        raise HTTPException(status_code=404, detail="Correção não encontrada.")

    correction.review_status = payload.review_status
    correction.review_note = payload.review_note
    if payload.review_status == "pendente":
        correction.reviewed_at = None
    else:
        correction.reviewed_at = datetime.now(timezone.utc)

    if payload.review_status == "ajustada":
        if payload.suggested_text is not None:
            correction.suggested_text = payload.suggested_text
        if payload.justification is not None:
            correction.justification = payload.justification

    await db.commit()
    await db.refresh(correction)
    return CorrectionResponse.model_validate(correction)


def _filter_corrections(
    corrections: list,
    *,
    for_sei: bool = False,
    review_statuses: set[str] | None = None,
) -> list:
    if for_sei:
        allowed = SEI_APPLICABLE_STATUSES
    elif review_statuses is not None:
        allowed = review_statuses
    else:
        return list(corrections)
    return [c for c in corrections if getattr(c, "review_status", None) in allowed]


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
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes da análise com correções (filtro opcional para SEI)."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
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
        analysis.corrections, for_sei=for_sei, review_statuses=statuses
    )
    if for_sei or statuses is not None:
        resp.corrections = [CorrectionResponse.model_validate(c) for c in filtered]
    resp.tokens_estimated = estimate_tokens(analysis)
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
    "/{analysis_id}/report",
    response_model=ReportResponse,
    summary="Relatório da análise",
    description="Retorna o relatório completo de uma análise finalizada.",
)
async def get_report(
    analysis_id: uuid.UUID,
    for_sei: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Gera relatório consolidado."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    raw = _filter_corrections(analysis.corrections, for_sei=for_sei) if for_sei else analysis.corrections
    corrections = [CorrectionResponse.model_validate(c) for c in raw]

    category_counts = dict(Counter(c.category for c in corrections))
    severity_counts = dict(Counter(c.severity for c in corrections))

    return ReportResponse(
        analysis_id=analysis.id,
        document_name=analysis.document.filename_original,
        document_id=analysis.document_id,
        status=analysis.status,
        scores=_score_details(analysis),
        risk_level=analysis.risk_level,
        total_corrections=len(corrections),
        corrections_by_category=category_counts,
        corrections_by_severity=severity_counts,
        corrections=corrections,
        final_opinion=analysis.final_opinion,
        analyzed_at=analysis.completed_at,
        tokens_estimated=estimate_tokens(analysis),
    )


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
        out.append(resp)
    return out


def _get_current_model() -> str:
    """Retorna o nome do modelo LLM configurado."""
    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
    }
    return model_map.get(settings.llm_provider, "unknown")
