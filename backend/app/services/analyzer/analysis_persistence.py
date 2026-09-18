"""Persistência e finalização da análise — extraído de `engine.py`.

`persist_item_outcomes` materializa os resultados da fase concorrente
(grounding, fail-closed jurídico, progresso por item). `finalize_analysis`
gera a pontuação e carimba o status final.
"""

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Correction
from app.services.analyzer.evidence_gate import detect_regime, evaluate_finding
from app.services.analyzer.grounding import (
    is_legal_basis_valid,
    is_original_text_grounded,
    should_fail_closed_legal,
)
from app.services.analyzer.scoring import (
    calculate_fallback_scores,
    generate_scores,
    sanitize_scores,
)
from app.utils.metrics import metrics

logger = logging.getLogger(__name__)


async def persist_item_outcomes(
    db: AsyncSession,
    analysis,
    document,
    document_id,
    items_context: list,
    results: list,
    valid_refs,
    total_work: int,
    budget_truncated: bool,
) -> dict:
    """Persiste correções item a item + progresso; retorna resumo da rodada."""
    analyzed_count = 0
    pending_reviews: list = []
    all_corrections: list[dict] = []
    coverage_incomplete = False
    successfully_analyzed_ids: list[str] = []
    failed_item_ids: list[str] = []
    try:
        _items_all = list(getattr(document, "items", None) or [it for it, _ in items_context])
    except Exception:
        _items_all = [it for it, _ in items_context]
    doc_text = " ".join(getattr(it, "content", "") or "" for it in _items_all)
    regime = detect_regime(doc_text)

    for (item, legal_context), outcome in zip(items_context, results, strict=False):
        if isinstance(outcome, Exception):
            coverage_incomplete = True
            failed_item_ids.append(str(item.id))
            logger.warning(
                "Erro ao analisar item %s do documento %s: %s",
                item.item_number, document_id, outcome,
            )
            continue

        correction_objs = []
        for correction_data in outcome:
            if correction_data.get("_coverage_errors"):
                coverage_incomplete = True
            gate = evaluate_finding(
                correction_data, item.content or "", doc_text, regime, valid_refs
            )
            if not gate.passed:
                metrics.inc(f"evidence_gate_rejected_{gate.gate.lower()}")
                logger.warning(
                    "evidence_gate %s rejeitou item %s: %s",
                    gate.gate,
                    item.item_number,
                    gate.reason,
                )
                continue
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
        successfully_analyzed_ids.append(str(item.id))
        analysis.analyzed_items = analyzed_count
        await db.commit()

        logger.info(
            "Item %s analisado (%d/%d): %d correções",
            item.item_number,
            analyzed_count,
            len(document.items),
            len(outcome),
        )

    # Atualiza snapshot com o que de fato concluiu vs falhou (elegível a reanalyze)
    snapshot = dict(analysis.run_snapshot or {})
    snapshot["analyzed_item_ids"] = successfully_analyzed_ids
    snapshot["failed_item_ids"] = failed_item_ids
    snapshot["regime"] = regime
    analysis.run_snapshot = snapshot
    await db.commit()

    if analyzed_count < total_work or budget_truncated:
        coverage_incomplete = True

    return {
        "analyzed_count": analyzed_count,
        "coverage_incomplete": coverage_incomplete,
        "pending_reviews": pending_reviews,
        "all_corrections": all_corrections,
    }


async def finalize_analysis(
    db: AsyncSession,
    analysis,
    document,
    llm,
    all_corrections: list[dict],
    total_work: int,
    coverage_incomplete: bool,
    budget_truncated: bool,
) -> None:
    """Gera pontuação, carimba status final e atualiza o documento."""
    analysis_id = analysis.id
    try:
        raw_scores = await generate_scores(llm, all_corrections, total_work)
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
        scores = calculate_fallback_scores(all_corrections, total_work)
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
        if budget_truncated:
            analysis.error_message = (
                "Análise preliminar de itens prioritários concluída. "
                "Para auditar os demais trechos substantivos, utilize "
                '"Reanalisar faltantes".'
            )
        else:
            analysis.error_message = (
                "Análise concluída, mas alguns trechos falharam. "
                "Não trate todos os itens como adequados; "
                'use "Reanalisar faltantes" para completar.'
            )
    else:
        analysis.status = "completed"
        analysis.error_message = None
    analysis.completed_at = datetime.now(timezone.utc)

    # Atualizar status do documento
    document.status = "completed"
    if coverage_incomplete and analysis.error_message:
        document.error_message = analysis.error_message

    await db.flush()

    logger.info(
        "Análise %s concluída (%s): %d itens, %d correções, nota %.1f",
        analysis_id,
        analysis.status,
        total_work,
        len(all_corrections),
        float(analysis.score_overall) if analysis.score_overall is not None else 0.0,
    )
