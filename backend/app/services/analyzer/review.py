"""
Revisão cruzada das correções geradas pelo LLM (Fase 2.2).

Executa uma segunda passagem sobre as correções de cada item para validar
consistência: sem inventar lei, sem reduzir competitividade, sem contradizer
o texto original. Cada correção recebe um status de revisão que fica
persistido na tabela `corrections`.
"""

import logging
from datetime import datetime, timezone

from app.services.analyzer.json_utils import parse_json_response
from app.services.analyzer.prompts import REVIEW_PROMPT, REVIEW_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

VALID_REVIEW_STATUSES = {"aprovada", "rejeitada", "ajustada"}


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

    normalized = [
        _normalize_decision(d, len(corrections))
        for d in decisions
        if isinstance(d, dict)
    ]
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


def _normalize_decision(decision: dict, total: int) -> dict:
    """Normaliza uma decisão do revisor para valores seguros."""
    status = str(decision.get("status", "aprovada")).lower()
    if status not in VALID_REVIEW_STATUSES:
        status = "aprovada"

    try:
        index = int(decision.get("correction_index", 0))
    except (TypeError, ValueError):
        index = 0
    index = max(0, min(index, total - 1)) if total > 0 else 0

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


def apply_review_decisions(correction_objs: list, decisions: list[dict]) -> list[dict]:
    """
    Aplica as decisões do revisor nos objetos Correction persistidos.

    - Correções aprovadas/ajustadas permanecem (ajustadas são atualizadas).
    - Correções rejeitadas ficam marcadas como tal (mantidas no banco para
      auditoria, mas excluídas do conjunto final de correções válidas).
    - Correções sem decisão permanecem como "pendente".

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

    return [
        _correction_to_dict(obj)
        for obj in correction_objs
        if obj.review_status in ("aprovada", "ajustada", "pendente")
    ]


def _correction_to_dict(obj) -> dict:
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
