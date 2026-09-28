"""Miss-hunter v1: 2ª passada seletiva nos itens que a 1ª deixou "ok".

Só roda com `MISS_HUNTER_ENABLED=true` (default OFF — cada alvo custa
~1 call/lote fora do orçamento ANALYSIS_MAX_LLM_CALLS) e pula quando a
cobertura já veio incompleta (orçamento estourou: o básico primeiro).

Achados do hunter passam pelo MESMO funil fail-closed da 1ª passada
(evidence_gate em persist_item_outcomes + revisão cruzada + supervisor):
vazio honesto continua vazio, achado forçado morre no gate.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.analyzer.analysis_persistence import persist_item_outcomes
from app.services.analyzer.analysis_phases import _run_cross_review
from app.services.analyzer.supervisor import _run_supervisor_rereview
from app.services.analyzer.batching import chunk_batches, get_batch_size
from app.services.analyzer.document_inventory import (
    build_inventory,
    format_document_facts,
)
from app.services.analyzer.item_analysis import (
    analyze_batch_hunter_llm,
    analyze_item_hunter_llm,
)

logger = logging.getLogger(__name__)

_SNAPSHOT_KEYS = (
    "analyzed_item_ids",
    "failed_item_ids",
    "origin_correction_ids",
)


def select_hunter_targets(pending_reviews: list, max_items: int) -> list:
    """Itens analisados com zero correções sobreviventes — alvos da 2ª passada.

    `pending_reviews` só contém itens que NÃO falharam (exceções dão `continue`
    antes do append em persist_item_outcomes), então lista vazia aqui = "ok"
    do ponto de vista do sistema, não erro a reanalisar.
    """
    cap = max(0, int(max_items or 0))
    targets = [
        (item, ctx) for item, ctx, objs in pending_reviews if not objs
    ]
    return targets[:cap] if cap else []


async def _analyze_hunter_concurrent(
    llm, hunter_context: list, document_facts: str
) -> list:
    semaphore = asyncio.Semaphore(max(1, settings.analysis_concurrency))

    async def _hunt_one(item, legal_context):
        async with semaphore:
            return await analyze_item_hunter_llm(
                llm, item, legal_context, document_facts=document_facts
            )

    async def _hunt_batch(chunk):
        async with semaphore:
            try:
                mapped = await analyze_batch_hunter_llm(
                    llm, chunk, document_facts=document_facts
                )
            except Exception as exc:
                return [exc for _ in chunk]
            return [mapped.get(str(item.id), []) for item, _ in chunk]

    batch_size = get_batch_size()
    if batch_size <= 1:
        return await asyncio.gather(
            *(_hunt_one(item, ctx) for item, ctx in hunter_context),
            return_exceptions=True,
        )
    chunked = await asyncio.gather(
        *(_hunt_batch(chunk) for chunk in chunk_batches(hunter_context, batch_size)),
        return_exceptions=True,
    )
    results: list = []
    for chunk, outcome in zip(
        chunk_batches(hunter_context, batch_size), chunked, strict=False
    ):
        if isinstance(outcome, Exception):
            results.extend([outcome for _ in chunk])
        else:
            results.extend(outcome)
    return results


async def _run_miss_hunter(
    db: AsyncSession,
    analysis,
    document,
    document_id,
    llm,
    pending_reviews: list,
    retrieval_by_item: dict,
    valid_refs,
    *,
    budget_truncated: bool = False,
) -> list[dict]:
    """2ª passada do hunter; retorna dicts das correções válidas encontradas."""
    if not getattr(settings, "miss_hunter_enabled", False):
        return []
    if budget_truncated:
        logger.info(
            "Miss-hunter pulado: orçamento LLM estourou (cobertura incompleta)."
        )
        return []
    max_items = int(getattr(settings, "miss_hunter_max_items", 10) or 0)
    targets = select_hunter_targets(pending_reviews, max_items)
    if not targets:
        return []
    logger.info(
        "Miss-hunter: 2ª passada em %d itens ok (cap %d)",
        len(targets), max_items,
    )

    try:
        document_facts = format_document_facts(
            build_inventory(list(getattr(document, "items", None) or []))
        )
    except Exception:
        document_facts = ""

    results = await _analyze_hunter_concurrent(llm, targets, document_facts)

    snapshot = dict(analysis.run_snapshot or {})
    saved_snapshot = {k: list(snapshot.get(k) or []) for k in _SNAPSHOT_KEYS}
    saved_analyzed = getattr(analysis, "analyzed_items", None)
    try:
        hunter_outcome = await persist_item_outcomes(
            db,
            analysis,
            document,
            document_id,
            targets,
            results,
            valid_refs,
            len(targets),
            False,
            retrieval_by_item,
        )
    finally:
        merged = dict(analysis.run_snapshot or {})
        for k in _SNAPSHOT_KEYS:
            seen: set = set()
            merged[k] = [
                x
                for x in (saved_snapshot[k] + list(merged.get(k) or []))
                if not (x in seen or seen.add(x))
            ]
        analysis.run_snapshot = merged
        analysis.analyzed_items = saved_analyzed
        await db.flush()

    kept = await _run_cross_review(db, llm, hunter_outcome["pending_reviews"])
    kept.extend(
        await _run_supervisor_rereview(db, llm, hunter_outcome["pending_reviews"])
    )
    if kept:
        logger.info("Miss-hunter: %d correções resgatadas", len(kept))
    return kept
