"""Relatório consolidado da análise — extraído de `api/analysis.py`."""

import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis_filters import _filter_corrections
from app.api.analysis_scoring import _score_details, estimate_tokens
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.schemas.analysis import (
    Art6ChecklistItem,
    CorrectionResponse,
    ReportResponse,
)
from app.services.analyzer.art6_status import build_art6_checklist, summarize_art6_coverage

router = APIRouter(prefix="/analysis", tags=["Análise"])


@router.get(
    "/{analysis_id}/report",
    response_model=ReportResponse,
    summary="Relatório da análise",
    description="Retorna o relatório completo de uma análise finalizada.",
)
async def get_report(
    analysis_id: uuid.UUID,
    for_sei: bool = False,
    severity_min: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Gera relatório consolidado."""
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

    raw = _filter_corrections(
        analysis.corrections,
        for_sei=for_sei,
        severity_min=severity_min,
    )
    corrections = [CorrectionResponse.model_validate(c) for c in raw]

    category_counts = dict(Counter(c.category for c in corrections))
    severity_counts = dict(Counter(c.severity for c in corrections))

    items = list(analysis.document.items or []) if analysis.document else []
    art6_rows = build_art6_checklist(items, analysis.corrections)
    art6 = [Art6ChecklistItem(**row) for row in art6_rows]
    art6_summary = summarize_art6_coverage(art6_rows)

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
        art6_checklist=art6,
        art6_coverage=art6_summary["art6_coverage"],
        art6_meets_target=art6_summary["art6_meets_target"],
    )
