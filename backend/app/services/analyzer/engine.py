"""
Motor de análise de documentos.

Orquestra a análise item a item usando LLM em fases:
1. Carrega documento e seus itens do banco
2. Recupera contexto jurídico (RAG) por item — sequencial (usa a sessão DB)
3. Analisa os itens via LLM com concorrência limitada (sem acesso ao DB)
4. Persiste resultados sequencialmente, commitando progresso por item
5. Revisão cruzada (LLM concorrente) + aplicação sequencial das decisões
6. Gera pontuação consolidada via LLM

Seleção de itens → `item_selection`; fases concorrentes → `analysis_phases`;
persistência/finalização → `analysis_persistence`.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.analysis import Analysis
from app.models.document import Document
from app.services.analyzer.analysis_persistence import (
    finalize_analysis,
    persist_item_outcomes,
)
from app.services.analyzer.analysis_phases import (
    _analyze_items_concurrent,
    _retrieve_legal_context,
    _run_cross_review,
)
from app.services.analyzer.grounding import get_valid_legal_refs
from app.services.analyzer.item_selection import select_items_for_analysis
from app.services.analyzer.llm_access import (
    acquire_analysis_llm,
    build_orchestrator,
    calls_per_item,
)

logger = logging.getLogger(__name__)


async def run_analysis(
    db: AsyncSession,
    analysis_id,
    document_id,
) -> None:
    """
    Executa análise completa de um documento.

    Esta função roda em background e atualiza o status no banco
    conforme progride.
    """
    # Carregar análise
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        logger.error("Análise %s não encontrada", analysis_id)
        return

    # Carregar documento com itens
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        analysis.status = "error"
        analysis.error_message = "Documento não encontrado."
        await db.flush()
        return

    llm, policy = await acquire_analysis_llm(db, analysis, document, document_id)
    if llm is None:
        return

    mode = getattr(analysis, "analysis_mode", "multi_agent") or "multi_agent"
    orchestrator = build_orchestrator(mode)

    snapshot = dict(analysis.run_snapshot or {})
    only_ids = snapshot.get("only_item_ids")
    all_items = [
        i for i in document.items if getattr(i, "archived_at", None) is None
    ]
    if only_ids:
        id_set = {str(x) for x in only_ids}
        candidates = [i for i in all_items if str(i.id) in id_set]
    else:
        candidates = list(all_items)

    max_calls = int(getattr(settings, "analysis_max_llm_calls", 0) or 0)
    max_items = (
        max(1, max_calls // calls_per_item(mode)) if max_calls > 0 else None
    )
    work_items, skipped_headings, budget_truncated = select_items_for_analysis(
        candidates, max_items=max_items
    )
    if skipped_headings:
        logger.info(
            "Análise %s: %d tópicos/títulos ignorados (sem corpo substantivo)",
            analysis_id,
            len(skipped_headings),
        )
    if budget_truncated:
        logger.warning(
            "Análise %s: orçamento LLM limitou a %d cláusulas (mode=%s)",
            analysis_id,
            len(work_items),
            mode,
        )

    snapshot["skipped_heading_ids"] = [str(i.id) for i in skipped_headings]
    snapshot["analyzed_item_ids"] = [str(i.id) for i in work_items]
    snapshot["failed_item_ids"] = []
    snapshot["budget_truncated"] = budget_truncated
    snapshot["total_document_items"] = len(document.items)
    snapshot["total_work_items"] = len(work_items)
    analysis.run_snapshot = snapshot
    await db.commit()

    # --- Fase 1: contexto jurídico por item (sequencial — usa a sessão DB) ---
    items_context: list = []
    for item in work_items:
        legal_context = await _retrieve_legal_context(
            db,
            item,
            llm,
            allow_semantic=policy.cloud_embeddings,
            allow_llm_rerank=policy.llm_rerank,
        )
        items_context.append((item, legal_context))

    # --- Fase 2: análise LLM concorrente (sem acesso ao DB) ---
    results = await _analyze_items_concurrent(llm, orchestrator, items_context)

    valid_refs = await get_valid_legal_refs(db)

    # --- Fase 3: persistência sequencial + progresso por item ---
    outcome = await persist_item_outcomes(
        db,
        analysis,
        document,
        document_id,
        items_context,
        results,
        valid_refs,
        len(work_items),
        budget_truncated,
    )

    # Se nenhum item foi analisado, os provedores LLM estão indisponíveis:
    # marcar como erro e propagar para o worker não marcar o job como completed.
    if outcome["analyzed_count"] == 0:
        analysis.status = "error"
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.error_message = (
            "Nenhum item pôde ser analisado: todos os provedores LLM "
            "falharam (verifique quota/limites das chaves Gemini e Groq)."
        )
        await db.flush()
        logger.error(
            "Análise %s marcada como erro: nenhum item analisado "
            "(provedores LLM indisponíveis)",
            analysis_id,
        )
        raise RuntimeError(analysis.error_message)

    # --- Fase 2.2: revisão cruzada das correções (após análise completa) ---
    all_corrections = await _run_cross_review(db, llm, outcome["pending_reviews"])

    # --- Fase 4: pontuação + status final ---
    await finalize_analysis(
        db,
        analysis,
        document,
        llm,
        all_corrections,
        len(work_items),
        outcome["coverage_incomplete"],
        budget_truncated,
    )
