"""
Revisão cruzada das correções geradas pelo LLM (Fase 2.2).

Executa uma segunda passagem sobre as correções de cada item para validar
consistência: sem inventar lei, sem reduzir competitividade, sem contradizer
o texto original. Cada correção recebe um status de revisão que fica
persistido na tabela `corrections`.

Fail-closed: status inválido ou índice ausente/fora do intervalo NÃO aprova.
Achados jurídicos altos sem review válida permanecem `pendente` e fora do score.
"""

import logging
from datetime import datetime, timezone

from app.services.analyzer.json_utils import parse_json_response
from app.services.analyzer.prompts import REVIEW_PROMPT, REVIEW_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

VALID_REVIEW_STATUSES = {"aprovada", "rejeitada", "ajustada"}
_HIGH_SEVERITIES = frozenset({"alto", "critico"})
_HIGH_IMPORTANCES = frozenset({"alta", "critica"})


async def review_item_corrections(
    llm, item, corrections: list[dict], legal_context: str
) -> list[dict]:
    """
    Envia as correções de um item ao revisor e retorna as decisões normalizadas.

    Se a resposta do LLM for inválida, retorna lista vazia (sem perder as
    correções originais — o chamador decide como tratar).
    """
    if not corrections:
        return []

    user_prompt = REVIEW_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        item_content=item.content[:8000],
        legal_context=legal_context or "(nenhum contexto recuperado)",
        corrections_summary=_build_summary(corrections),
    )

    response = await llm.generate(REVIEW_SYSTEM_PROMPT, user_prompt)
    decisions = parse_json_response(response)

    # Aceitar {"review": [...]} ou uma lista direta de decisões
    if isinstance(decisions, dict):
        decisions = decisions.get("review", [])
    if not isinstance(decisions, list):
        logger.warning("Resposta do revisor inválida; correções mantidas")
        return []

    normalized = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        decision = _normalize_decision(d, len(corrections))
        if decision is not None:
            normalized.append(decision)
    logger.info(
        "Revisão do item %s: %d decisões",
        item.item_number,
        len(normalized),
    )
    return normalized


def _build_summary(corrections: list[dict]) -> str:
    """Monta a lista numerada de correções enviada ao revisor."""
    parts = []
    for i, c in enumerate(corrections):
        parts.append(
            f"[{i}] Categoria: {c.get('category', '?')} | "
            f"Severidade: {c.get('severity', '?')}\n"
            f"  Problema: {c.get('problem', '')}\n"
            f"  Trecho original: {c.get('original_text', '')}\n"
            f"  Texto sugerido: {c.get('suggested_text', '')}\n"
            f"  Fundamento: {c.get('legal_basis') or 'não informado'}\n"
            f"  Justificativa: {c.get('justification', '')}"
        )
    return "\n\n".join(parts)


def _normalize_decision(decision: dict, total: int) -> dict | None:
    """
    Normaliza uma decisão do revisor.

    Fail-closed: status inválido ou índice ausente/inválido → None (não aprova).
    """
    raw_status = decision.get("status")
    if raw_status is None or str(raw_status).strip() == "":
        logger.warning("Decisão de revisão sem status — ignorada (fail-closed)")
        return None

    status = str(raw_status).lower().strip()
    if status not in VALID_REVIEW_STATUSES:
        logger.warning(
            "Status de revisão inválido %r — não aprova (fail-closed)", raw_status
        )
        return None

    if "correction_index" not in decision:
        logger.warning("Decisão de revisão sem correction_index — ignorada (fail-closed)")
        return None

    try:
        index = int(decision["correction_index"])
    except (TypeError, ValueError):
        logger.warning(
            "correction_index inválido %r — ignorado (fail-closed)",
            decision.get("correction_index"),
        )
        return None

    if total <= 0 or index < 0 or index >= total:
        logger.warning(
            "correction_index fora do intervalo (%s, total=%s) — ignorado (fail-closed)",
            index,
            total,
        )
        return None

    return {
        "correction_index": index,
        "status": status,
        "note": str(decision.get("note", ""))[:2000],
        "adjusted_suggested_text": (
            str(decision.get("adjusted_suggested_text", "")).strip() or None
        ),
        "adjusted_justification": (
            str(decision.get("adjusted_justification", "")).strip() or None
        ),
    }


def _is_high_juridical(obj) -> bool:
    category = getattr(obj, "category", "") or ""
    severity = (getattr(obj, "severity", "") or "").lower()
    importance = (getattr(obj, "importance", "") or "").lower()
    return category == "juridica" and (
        severity in _HIGH_SEVERITIES or importance in _HIGH_IMPORTANCES
    )


def apply_review_decisions(correction_objs: list, decisions: list[dict]) -> list[dict]:
    """
    Aplica as decisões do revisor nos objetos Correction persistidos.

    - Correções aprovadas/ajustadas permanecem (ajustadas são atualizadas).
    - Correções rejeitadas ficam marcadas como tal (mantidas no banco para
      auditoria, mas excluídas do conjunto final de correções válidas).
    - Correções sem decisão permanecem como "pendente".
    - Achados jurídicos altos sem review válida ficam `pendente` e fora do score.

    Retorna a lista de dicts das correções válidas (para pontuação/benchmark).
    """
    for obj in correction_objs:
        obj.review_status = "pendente"
        obj.review_note = None
        obj.reviewed_at = None

    for d in decisions:
        idx = d["correction_index"]
        if idx < 0 or idx >= len(correction_objs):
            logger.warning("Decisão de revisão com índice fora do intervalo: %d", idx)
            continue

        obj = correction_objs[idx]
        obj.review_status = d["status"]
        obj.review_note = d["note"] or None
        obj.reviewed_at = datetime.now(timezone.utc)

        if d["status"] == "ajustada":
            if d["adjusted_suggested_text"]:
                obj.suggested_text = d["adjusted_suggested_text"]
            if d["adjusted_justification"]:
                obj.justification = d["adjusted_justification"]

    kept: list[dict] = []
    for obj in correction_objs:
        if obj.review_status in ("aprovada", "ajustada"):
            kept.append(correction_to_dict(obj))
        elif obj.review_status == "pendente":
            if _is_high_juridical(obj):
                # Fora do score/cópia até review válida
                continue
            kept.append(correction_to_dict(obj))
    return kept


def correction_to_dict(obj) -> dict:
    """Converte um objeto Correction em dict para pontuação/benchmark."""
    return {
        "category": obj.category,
        "severity": obj.severity,
        "situation": obj.situation,
        "problem": obj.problem,
        "risk": obj.risk,
        "original_text": obj.original_text,
        "suggested_text": obj.suggested_text,
        "justification": obj.justification,
        "legal_basis": obj.legal_basis,
        "importance": obj.importance,
    }
