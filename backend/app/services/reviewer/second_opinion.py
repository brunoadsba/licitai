"""
Segunda opinião via LLM local (opcional).

Se `REVIEWER_SECOND_OPINION` estiver desligado ou o provider falhar (429/500),
devolve a sugestão determinística intacta (fail-closed = sem piorar).
Quando ligada, ajusta confiança em ±0.06 e acrescenta nota curta.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_REVIEW_PROMPT = """Você é um revisor de TR de licitação (Lei 14.133/21).
Dado um achado com sugestão determinística, valide se a sugestão procede.
Responda APENAS JSON: {"ok": true|false, "delta": -0.06..0.06, "note": "frase curta em PT-BR"}.
Sem cadeia de pensamento, sem markdown."""


async def refine_with_llm(suggestion, *, correction, item_content: str | None) -> object:
    """
    Tenta refinar a sugestão com LLM local. Nunca quebra o fluxo.
    Retorna a mesma sugestão (mutada levemente) em caso de falha.
    """
    if os.getenv("REVIEWER_SECOND_OPINION", "0") not in ("1", "true", "True"):
        return suggestion

    try:
        from app.services.llm import get_llm_provider  # lazy p/ não quebrar import em testes

        llm = get_llm_provider()
        payload = {
            "correction_id": suggestion.correction_id,
            "suggestion": suggestion.suggestion,
            "confidence": suggestion.confidence,
            "reason": suggestion.reason,
            "problem": getattr(correction, "problem", "")[:400],
            "suggested_text": (getattr(correction, "suggested_text", "") or "")[:400],
        }
        # Chamada curta, sem RAG; ignora estritamente falhas.
        resp = await llm.agenerate(
            prompt=_REVIEW_PROMPT,
            context=f"Achado: {payload}\nTrecho do item: {(item_content or '')[:500]}",
            max_tokens=120,
        )
        # llm.agenerate não existe em todos os providers — fallback simples
        import json as _json

        text = getattr(resp, "text", None) or getattr(resp, "content", None) or str(resp)
        data = _json.loads(text) if isinstance(text, str) and text.strip().startswith("{") else {}
        delta = float(data.get("delta", 0)) if isinstance(data.get("delta"), (int, float)) else 0
        delta = max(-0.06, min(0.06, delta))
        note = str(data.get("note", "")).strip()[:120] if data.get("note") else ""
        suggestion.confidence = max(0.0, min(1.0, float(suggestion.confidence) + delta))
        if note:
            suggestion.reason = f"{suggestion.reason} · 2ª opinião: {note}"
        return suggestion
    except Exception as exc:  # noqa: BLE001 — consultivo, nunca quebra
        logger.debug("reviewer.second_opinion.skip: %s", exc)
        return suggestion
