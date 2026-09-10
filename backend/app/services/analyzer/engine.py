"""
Motor de análise de documentos.

Orquestra a análise item a item usando LLM em fases:
1. Carrega documento e seus itens do banco
2. Recupera contexto jurídico (RAG) por item — sequencial (usa a sessão DB)
3. Analisa os itens via LLM com concorrência limitada (sem acesso ao DB)
4. Persiste resultados sequencialmente, commitando progresso por item
5. Revisão cruzada (LLM concorrente) + aplicação sequencial das decisões
6. Gera pontuação consolidada via LLM
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.services.agents.orchestrator import MultiAgentOrchestrator
from app.services.agents.legal_agent import LegalAgent
from app.services.agents.structural_agent import StructuralAgent
from app.services.analyzer.item_analysis import analyze_item_llm
from app.services.analyzer.review import (
    apply_review_decisions,
    correction_to_dict,
    review_item_corrections,
)
from app.services.analyzer.grounding import (
    get_valid_legal_refs,
    is_legal_basis_valid,
    is_original_text_grounded,
    should_fail_closed_legal,
)
from app.services.analyzer.scoring import (
    calculate_fallback_scores,
    generate_scores,
    sanitize_scores,
)
from app.services.llm import get_llm_provider
from app.services.rag.retriever import retrieve
from app.utils.metrics import metrics

logger = logging.getLogger(__name__)


def _build_orchestrator(mode: str) -> MultiAgentOrchestrator | None:
    if mode == "economic":
        return MultiAgentOrchestrator([LegalAgent(), StructuralAgent()])
    if mode == "multi_agent":
        return MultiAgentOrchestrator()
    return None


def _calls_per_item(mode: str) -> int:
    if mode == "economic":
        return 2
    if mode == "single":
        return 1
    return 4


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

    # Iniciar análise
    analysis.status = "running"
    analysis.started_at = datetime.now(timezone.utc)
    analysis.total_items = len(document.items)
    await db.commit()

    # Obter provedor LLM
    try:
        llm = get_llm_provider()
    except (ValueError, RuntimeError) as e:
        analysis.status = "error"
        analysis.error_message = str(e)
        await db.flush()
        return

    mode = getattr(analysis, "analysis_mode", "multi_agent") or "multi_agent"
    orchestrator = _build_orchestrator(mode)

    snapshot = analysis.run_snapshot or {}
    only_ids = snapshot.get("only_item_ids")
    all_items = [
        i for i in document.items if getattr(i, "archived_at", None) is None
    ]
    if only_ids:
        id_set = {str(x) for x in only_ids}
        work_items = [i for i in all_items if str(i.id) in id_set]
    else:
        work_items = list(all_items)

    budget_truncated = False
    max_calls = int(getattr(settings, "analysis_max_llm_calls", 0) or 0)
    if max_calls > 0:
        max_items = max(1, max_calls // _calls_per_item(mode))
        if len(work_items) > max_items:
            work_items = work_items[:max_items]
            budget_truncated = True
            logger.warning(
                "Análise %s: orçamento LLM limitou a %d itens (mode=%s)",
                analysis_id,
                max_items,
                mode,
            )

    analysis.total_items = len(work_items)
    await db.commit()

    # --- Fase 1: contexto jurídico por item (sequencial — usa a sessão DB) ---
    items_context: list[tuple[DocumentItem, str]] = []
    for item in work_items:
        legal_context = await _retrieve_legal_context(db, item)
        items_context.append((item, legal_context))

    # --- Fase 2: análise LLM concorrente (sem acesso ao DB) ---
    results = await _analyze_items_concurrent(llm, orchestrator, items_context)

    valid_refs = await get_valid_legal_refs(db)

    # --- Fase 3: persistência sequencial + progresso por item ---
    analyzed_count = 0
    pending_reviews: list[tuple[DocumentItem, str, list[Correction]]] = []
    all_corrections: list[dict] = []
    coverage_incomplete = False

    for (item, legal_context), outcome in zip(items_context, results, strict=False):
        if isinstance(outcome, Exception):
            coverage_incomplete = True
            logger.warning(
                "Erro ao analisar item %s do documento %s: %s",
                item.item_number, document_id, outcome,
            )
            continue

        correction_objs = []
        for correction_data in outcome:
            if correction_data.get("_coverage_errors"):
                coverage_incomplete = True
            grounded = is_original_text_grounded(
                correction_data.get("original_text", ""), item.content or ""
            )
            legal_valid = is_legal_basis_valid(
                correction_data.get("legal_basis"), valid_refs
            )
            importance = correction_data.get("importance", "media")
            legal_basis = correction_data.get("legal_basis")
            severity = correction_data.get("severity", "medio")
            fail_closed = should_fail_closed_legal(
                legal_valid, severity=severity, importance=importance
            )
            if legal_valid is False:
                legal_basis = None
                if fail_closed:
                    # Fail-closed: não rebaixa silenciosamente — rejeita o achado.
                    pass
                elif importance in ("alta", "critica"):
                    importance = "media"
            if severity == "critico":
                if correction_data.get("category") != "juridica" or not grounded or legal_valid is not True:
                    severity = "alto"
            excerpt = correction_data.get("original_text", "") or ""
            excerpt_hash = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()[:16] if excerpt else None
            evidence = {
                "excerpt_hash": excerpt_hash,
                "prompt_version": "v1",
                "corpus_version": str(len(valid_refs)),
                "grounded": grounded,
                "legal_valid": legal_valid,
                "fail_closed_legal": fail_closed,
                "item_number": item.item_number,
            }
            if correction_data.get("_coverage_errors"):
                evidence["coverage_errors"] = correction_data["_coverage_errors"]
            correction = Correction(
                analysis_id=analysis.id,
                document_item_id=item.id,
                category=correction_data.get("category", "tecnica"),
                severity=severity,
                situation=correction_data.get("situation", ""),
                problem=correction_data.get("problem", ""),
                risk=correction_data.get("risk", ""),
                original_text=correction_data.get("original_text", ""),
                suggested_text=correction_data.get("suggested_text", ""),
                justification=correction_data.get("justification", ""),
                legal_basis=legal_basis,
                importance=importance,
                agent_origin=correction_data.get("agent_origin"),
                evidence=evidence,
            )
            if not grounded:
                correction.review_status = "rejeitada"
                correction.review_note = "original_text não encontrado no item (possível alucinação)"
                correction.reviewed_at = datetime.now(timezone.utc)
                metrics.inc("review_rejected")
            elif fail_closed:
                correction.review_status = "rejeitada"
                correction.review_note = (
                    "legal_basis inválido no corpus (fail-closed para severidade alta/crítica)"
                )
                correction.reviewed_at = datetime.now(timezone.utc)
                metrics.inc("review_rejected")
            db.add(correction)
            correction_objs.append(correction)
            if grounded and not fail_closed:
                all_corrections.append(correction_data)
            elif not grounded:
                logger.warning(
                    "Correção rejeitada por falta de grounding no item %s: %s",
                    item.item_number,
                    correction_data.get("original_text", "")[:80],
                )
            elif fail_closed:
                logger.warning(
                    "Correção rejeitada por legal_basis inválido (fail-closed) no item %s",
                    item.item_number,
                )

        corrigiveis = [c for c in correction_objs if c.review_status != "rejeitada"]
        pending_reviews.append((item, legal_context, corrigiveis))
        analyzed_count += 1
        analysis.analyzed_items = analyzed_count
        await db.commit()

        logger.info(
            "Item %s analisado (%d/%d): %d correções",
            item.item_number,
            analyzed_count,
            len(document.items),
            len(outcome),
        )

    if analyzed_count < len(work_items) or budget_truncated:
        coverage_incomplete = True

    # Se nenhum item foi analisado, os provedores LLM estão indisponíveis:
    # marcar como erro em vez de reportar sucesso falso.
    if analyzed_count == 0:
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
        return

    # --- Fase 2.2: revisão cruzada das correções (após análise completa) ---
    all_corrections = await _run_cross_review(db, llm, pending_reviews)

    # Gerar pontuação consolidada
    try:
        raw_scores = await generate_scores(llm, all_corrections, len(work_items))
        scores = sanitize_scores(raw_scores)

        analysis.score_overall = scores["score_overall"]
        analysis.score_juridical = scores["score_juridical"]
        analysis.score_technical = scores["score_technical"]
        analysis.score_writing = scores["score_writing"]
        analysis.score_structural = scores["score_structural"]
        analysis.risk_level = scores.get("risk_level", "medio")
        analysis.final_opinion = scores.get("final_opinion", "")

        if analysis.score_overall is None:
            raise ValueError("Score ausente")

    except Exception:
        logger.exception("Erro ao gerar pontuação via LLM para análise %s; aplicando cálculo determinístico de fallback", analysis_id)
        scores = calculate_fallback_scores(all_corrections, len(work_items))
        analysis.score_overall = scores["score_overall"]
        analysis.score_juridical = scores["score_juridical"]
        analysis.score_technical = scores["score_technical"]
        analysis.score_writing = scores["score_writing"]
        analysis.score_structural = scores["score_structural"]
        analysis.risk_level = scores["risk_level"]
        analysis.final_opinion = scores["final_opinion"]

    # Finalizar
    if coverage_incomplete:
        analysis.status = "completed_with_errors"
        msg = (
            "Análise concluída com cobertura incompleta de agentes/itens. "
            "Não tratar todos os itens como adequados; reexecute os faltantes."
        )
        if budget_truncated:
            msg += " Orçamento ANALYSIS_MAX_LLM_CALLS atingido."
        analysis.error_message = msg
    else:
        analysis.status = "completed"
        analysis.error_message = None
    analysis.completed_at = datetime.now(timezone.utc)

    # Atualizar status do documento
    document.status = "completed"

    await db.flush()

    logger.info(
        "Análise %s concluída (%s): %d itens, %d correções, nota %.1f",
        analysis_id,
        analysis.status,
        len(work_items),
        len(all_corrections),
        float(analysis.score_overall) if analysis.score_overall is not None else 0.0,
    )


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


async def _retrieve_legal_context(db: AsyncSession, item: DocumentItem) -> str:
    """Busca artigos relevantes no corpus jurídico e formata para o prompt."""
    try:
        chunks = await retrieve(
            db,
            query=f"{item.title or ''} {item.content}",
            top_k=4,
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
