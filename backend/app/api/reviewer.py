"""
Endpoints do revisor-assistente (consultivo).

Sugestões determinísticas locais (grounding + legal_basis + placeholder + fail-closed)
com opcional 2ª opinião LLM. Nunca auto-aprova; humano decide e recalcula scores.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.services.analyzer.grounding import get_valid_legal_refs
from app.services.reviewer.checks import suggest_for_correction
from app.services.reviewer.schemas import ReviewSuggestion, ReviewSuggestionsResponse
from app.services.reviewer.second_opinion import refine_with_llm
from app.utils.metrics import metrics
from pydantic import BaseModel

router = APIRouter(prefix="/analysis", tags=["Análise"])


class ReviewTrackIn(BaseModel):
    suggestion: str
    decision: str
    confidence: float | None = None


async def _load_analysis(
    db: AsyncSession, analysis_id: uuid.UUID
) -> tuple[Analysis, dict[str, str]]:
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
    items_by_id = {
        str(it.id): (it.content or "")
        for it in (analysis.document.items or [])
    }
    return analysis, items_by_id


@router.get(
    "/{analysis_id}/review-suggestions",
    response_model=ReviewSuggestionsResponse,
    summary="Sugestões do revisor-assistente",
    description=(
        "Lista de sugestões (aprovar/rejeitar/ajustar) com confiança e motivo. "
        "Consultivo: humano decide; só aprovada/ajustada vai para o SEI."
    ),
)
async def list_review_suggestions(
    analysis_id: uuid.UUID,
    pending_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    analysis, items_by_id = await _load_analysis(db, analysis_id)
    valid_refs = await get_valid_legal_refs(db)

    corrections = list(analysis.corrections or [])
    if pending_only:
        corrections = [c for c in corrections if (getattr(c, "review_status", None) or "pendente") == "pendente"]

    suggestions: list[ReviewSuggestion] = []
    for c in corrections:
        item_content = items_by_id.get(str(getattr(c, "document_item_id", "")), "")
        s = suggest_for_correction(c, item_content=item_content, valid_refs=valid_refs)
        s = await refine_with_llm(s, correction=c, item_content=item_content)  # type: ignore[assignment]
        suggestions.append(s)

    # Ordenar como o guiado: rejeitar/ajustar críticos primeiro, depois aprovar
    order = {"rejeitar": 0, "ajustar": 1, "aprovar": 2}
    suggestions.sort(key=lambda x: (order.get(x.suggestion, 9), -x.confidence))

    return ReviewSuggestionsResponse(
        analysis_id=str(analysis.id),
        total=len(analysis.corrections or []),
        pending=len(suggestions) if pending_only else len([c for c in (analysis.corrections or []) if (getattr(c, "review_status", None) or "pendente") == "pendente"]),
        suggestions=suggestions,
    )


@router.get(
    "/{analysis_id}/review-suggestions/{correction_id}",
    response_model=ReviewSuggestion,
    summary="Sugestão para uma correção",
)
async def get_review_suggestion(
    analysis_id: uuid.UUID,
    correction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    analysis, items_by_id = await _load_analysis(db, analysis_id)
    valid_refs = await get_valid_legal_refs(db)

    target = next((c for c in (analysis.corrections or []) if str(getattr(c, "id", "")) == str(correction_id)), None)
    if not target:
        raise HTTPException(status_code=404, detail="Correção não encontrada nesta análise.")

    item_content = items_by_id.get(str(getattr(target, "document_item_id", "")), "")
    s = suggest_for_correction(target, item_content=item_content, valid_refs=valid_refs)
    s = await refine_with_llm(s, correction=target, item_content=item_content)  # type: ignore[assignment]
    return s


@router.post(
    "/{analysis_id}/review-suggestions/{correction_id}/track",
    summary="Rastrear aceitação da sugestão (métrica)",
)
async def track_suggestion(
    analysis_id: uuid.UUID,
    correction_id: uuid.UUID,
    payload: ReviewTrackIn,
):
    accepted = payload.suggestion == payload.decision or (
        payload.suggestion == "aprovar" and payload.decision == "aprovada"
    ) or (
        payload.suggestion == "rejeitar" and payload.decision == "rejeitada"
    )
    if accepted:
        metrics.inc("review_suggestion_accepted")
    else:
        metrics.inc("review_suggestion_overridden")
    metrics.inc("review_suggestion_tracked")
    return {"accepted": accepted}
