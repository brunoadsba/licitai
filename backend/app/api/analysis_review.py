"""Revisão humana de correções + pendências — extraído de `api/analysis.py`."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis_filters import SEVERITY_RANK
from app.api.analysis_scoring import recalculate_analysis_scores
from app.database import get_db
from app.models.analysis import Analysis, Correction
from app.schemas.analysis import (
    CorrectionResponse,
    CorrectionReviewUpdate,
    PendingSummaryItem,
    PendingSummaryResponse,
)
from app.utils.metrics import metrics

router = APIRouter(prefix="/analysis", tags=["Análise"])


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

    await recalculate_analysis_scores(db, correction.analysis_id)
    await db.commit()
    await db.refresh(correction)

    status = payload.review_status
    if status == "aprovada":
        metrics.inc("review_approved")
    elif status == "rejeitada":
        metrics.inc("review_rejected")
    elif status == "ajustada":
        metrics.inc("review_adjusted")

    return CorrectionResponse.model_validate(correction)


def _is_priority_pending(c: Correction) -> bool:
    if getattr(c, "review_status", None) != "pendente":
        return False
    if getattr(c, "category", None) == "estrutural":
        return True
    return SEVERITY_RANK.get(getattr(c, "severity", "") or "", -1) >= SEVERITY_RANK["alto"]


@router.get(
    "/pending-summary",
    response_model=PendingSummaryResponse,
    summary="Pendências prioritárias de revisão",
)
async def pending_summary(db: AsyncSession = Depends(get_db)):
    """Docs com análise concluída e correções pendentes alto/crítico/estrutural."""
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document),
        )
        .where(Analysis.status.in_(["completed", "completed_with_errors"]))
        .order_by(Analysis.completed_at.desc())
    )
    analyses = result.scalars().unique().all()
    seen_docs: set[uuid.UUID] = set()
    items: list[PendingSummaryItem] = []
    for analysis in analyses:
        doc_id = analysis.document_id
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        pending = [c for c in analysis.corrections if _is_priority_pending(c)]
        if not pending:
            continue
        doc = analysis.document
        items.append(
            PendingSummaryItem(
                document_id=doc_id,
                analysis_id=analysis.id,
                filename=doc.filename_original if doc else "?",
                pending_priority=len(pending),
                status=analysis.status,
            )
        )
    total_corrections = sum(item.pending_priority for item in items)
    return PendingSummaryResponse(total=total_corrections, items=items)
