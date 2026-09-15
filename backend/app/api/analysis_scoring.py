"""Scoring de análises (tokens, recálculo pós-revisão) — extraído de `api/analysis.py`."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis
from app.schemas.analysis import ScoreDetail
from app.services.analyzer.scoring import calculate_deterministic_scores


def estimate_tokens(analysis: Analysis) -> int:
    base = (analysis.total_items or 0) * 900 + (analysis.analyzed_items or 0) * 100
    corr = len(getattr(analysis, "corrections", []) or [])
    return base + corr * 350 + 800


async def recalculate_analysis_scores(
    db: AsyncSession, analysis_id: uuid.UUID
) -> None:
    """Recalcula notas/risco após revisão humana (exclui rejeitadas)."""
    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        return

    active = [
        {
            "category": c.category,
            "severity": c.severity,
            "problem": c.problem,
        }
        for c in (analysis.corrections or [])
        if getattr(c, "review_status", None) != "rejeitada"
    ]
    scores = calculate_deterministic_scores(active, analysis.total_items or 0)
    analysis.score_overall = scores["score_overall"]
    analysis.score_juridical = scores["score_juridical"]
    analysis.score_technical = scores["score_technical"]
    analysis.score_writing = scores["score_writing"]
    analysis.score_structural = scores["score_structural"]
    analysis.risk_level = scores["risk_level"]
    analysis.final_opinion = scores["final_opinion"]


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
