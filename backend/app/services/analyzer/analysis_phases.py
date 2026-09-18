"""Fases concorrentes da análise (RAG, LLM, revisão cruzada) — extraído de `engine.py`.

Não tocam no banco na fase concorrente: apenas leitura de atributos já
carregados; a persistência decide o que fazer com cada resultado.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import DocumentItem
from app.models.analysis import Correction
from app.services.agents.orchestrator import MultiAgentOrchestrator
from app.services.analyzer.item_analysis import analyze_item_llm
from app.services.analyzer.review import (
    apply_review_decisions,
    correction_to_dict,
    review_item_corrections,
)
from app.services.rag.retriever import retrieve

logger = logging.getLogger(__name__)


async def _analyze_items_concurrent(
    llm,
    orchestrator: MultiAgentOrchestrator | None,
    items_context: list[tuple[DocumentItem, str]],
) -> list[list[dict] | Exception]:
    """
    Executa a análise LLM dos itens com concorrência limitada.

    Não toca no banco: apenas leitura de atributos já carregados dos itens,
    o que é seguro sob concorrência. Exceções são devolvidas por posição
    (`return_exceptions=True`) para que a persistência decida o que fazer.
    """
    semaphore = asyncio.Semaphore(max(1, settings.analysis_concurrency))

    async def _analyze_one(item: DocumentItem, legal_context: str) -> list[dict]:
        async with semaphore:
            if orchestrator:
                return await orchestrator.analyze_item_multi(llm, item, legal_context)
            return await analyze_item_llm(llm, item, legal_context)

    total = len(items_context)
    if total > 1:
        logger.info(
            "Analisando %d itens com concorrência %d", total, settings.analysis_concurrency
        )

    return await asyncio.gather(
        *(_analyze_one(item, ctx) for item, ctx in items_context),
        return_exceptions=True,
    )


async def _retrieve_legal_context(
    db: AsyncSession, item: DocumentItem, llm=None
) -> str:
    """Busca artigos relevantes no corpus jurídico e formata para o prompt.

    `llm` opcional: só usado quando `rag_rerank_mode="llm"`; o chamador
    garante a trava de privacidade (sigiloso nunca vai a cloud).
    """
    try:
        chunks = await retrieve(
            db,
            query=f"{item.title or ''} {item.content}",
            top_k=4,
            llm=llm,
        )
    except Exception:
        logger.exception("Falha ao recuperar contexto jurídico")
        return ""

    if not chunks:
        return ""

    parts = []
    for c in chunks:
        parts.append(
            f"### {c.law_number} — {c.article}\n{c.text[:2500]}"
        )
    return "\n\n".join(parts)


async def _run_cross_review(
    db: AsyncSession,
    llm,
    pending_reviews: list[tuple[DocumentItem, str, list[Correction]]],
) -> list[dict]:
    """Revisa as correções de cada item (LLM concorrente) e aplica as decisões."""
    kept: list[dict] = []
    revisaveis = [
        (item, legal_context, correction_objs)
        for item, legal_context, correction_objs in pending_reviews
        if correction_objs
    ]
    if not revisaveis:
        return kept

    semaphore = asyncio.Semaphore(max(1, settings.analysis_concurrency))

    async def _review_one(item: DocumentItem, legal_context: str, correction_objs: list[Correction]):
        async with semaphore:
            corrections_dict = [correction_to_dict(obj) for obj in correction_objs]
            return await review_item_corrections(llm, item, corrections_dict, legal_context)

    decisions_or_exc = await asyncio.gather(
        *(_review_one(item, ctx, objs) for item, ctx, objs in revisaveis),
        return_exceptions=True,
    )

    # Aplicação sequencial das decisões (mutação de objetos ORM + flush)
    for (item, _ctx, correction_objs), outcome in zip(revisaveis, decisions_or_exc, strict=False):
        if isinstance(outcome, Exception):
            logger.warning(
                "Falha na revisão cruzada do item %s: %s",
                item.item_number, outcome,
            )
            for obj in correction_objs:
                obj.review_status = "pendente"
            kept.extend(correction_to_dict(obj) for obj in correction_objs)
            continue

        kept.extend(apply_review_decisions(correction_objs, outcome))

    await db.flush()
    logger.info("Revisão cruzada concluída: %d correções válidas", len(kept))
    return kept
