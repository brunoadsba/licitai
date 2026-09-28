"""Supervisor v1: segunda chance para achados altos ainda pendentes.

A decisão da máquina não libera o SEI. Jurídico alto permanece pendente
até o PATCH humano.
"""

import asyncio
import logging

from app.config import settings
from app.services.analyzer.batching import chunk_batches, get_batch_size
from app.services.analyzer.review import (
    apply_review_decisions,
    correction_to_dict,
    review_batch_corrections,
)

logger = logging.getLogger(__name__)

_HIGH_SEVERITIES = frozenset({"alto", "critico"})
_HIGH_IMPORTANCES = frozenset({"alta", "critica"})


def _is_high_pending(obj) -> bool:
    """Alvo da segunda chance: ainda pendente e alto/crítico."""
    if getattr(obj, "review_status", None) != "pendente":
        return False
    severity = (getattr(obj, "severity", "") or "").lower()
    importance = (getattr(obj, "importance", "") or "").lower()
    return severity in _HIGH_SEVERITIES or importance in _HIGH_IMPORTANCES


async def _run_supervisor_rereview(
    db, llm, pending_reviews, *, budget_truncated: bool = False
) -> list[dict]:
    """Segunda chance só para altos ainda pendentes.

    Custa ~1 call por lote. Pula quando o orçamento LLM já estourou.
    Retorna dicts que entram no score desta rodada.
    """
    if budget_truncated:
        logger.info("Supervisor pulado: orçamento LLM estourou.")
        return []
    if not getattr(settings, "supervisor_rereview_high", True):
        return []
    targets = [
        (item, ctx, [o for o in objs if _is_high_pending(o)])
        for item, ctx, objs in pending_reviews
    ]
    targets = [(item, ctx, objs) for item, ctx, objs in targets if objs]
    if not targets:
        return []

    semaphore = asyncio.Semaphore(max(1, settings.analysis_concurrency))

    async def _rereview_batch(chunk: list[tuple]):
        async with semaphore:
            try:
                payload = [
                    (item, ctx, [correction_to_dict(o) for o in objs])
                    for item, ctx, objs in chunk
                ]
                return await review_batch_corrections(llm, payload)
            except Exception as exc:
                return exc

    batch_size = get_batch_size()
    chunks = chunk_batches(targets, batch_size)
    outcomes = await asyncio.gather(
        *(_rereview_batch(chunk) for chunk in chunks),
        return_exceptions=True,
    )

    flipped: list[dict] = []
    applied = False
    for chunk, outcome in zip(chunks, outcomes, strict=False):
        if isinstance(outcome, Exception):
            logger.warning("Falha na re-review supervisora: %s", outcome)
            continue
        applied = True
        for item, _ctx, objs in chunk:
            kept = apply_review_decisions(objs, outcome.get(str(item.id), []))
            flipped.extend(kept)
    if applied:
        await db.flush()
        logger.info(
            "Supervisor v1: %d altos seguem no score; aprovação humana continua pendente",
            len(flipped),
        )
    return flipped
