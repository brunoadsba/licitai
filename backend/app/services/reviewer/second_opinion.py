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


async def refine_with_llm(
    suggestion,
    *,
    correction,
    item_content: str | None,
    classification: str | None = None,
) -> object:
    """
    Tenta refinar a sugestão com o provedor permitido pela classificação.
    Documento restrito sem Ollama devolve a sugestão intacta (não chama a nuvem).
    """
    if os.getenv("REVIEWER_SECOND_OPINION", "0") not in ("1", "true", "True"):
        return suggestion

    try:
        from app.services.llm.factory import get_llm_provider_for
        from app.services.privacy import resolve_policy

        llm = get_llm_provider_for(resolve_policy(classification))
        payload = {
            "correction_id": suggestion.correction_id,
            "suggestion": suggestion.suggestion,
            "confidence": suggestion.confidence,
            "reason": suggestion.reason,
            "problem": getattr(correction, "problem", "")[:400],
            "suggested_text": (getattr(correction, "suggested_text", "") or "")[:400],
        }
        prompt = f"{_REVIEW_PROMPT}\nAchado: {payload}\nTrecho do item: {(item_content or '')[:500]}"
        if hasattr(llm, "generate"):
            text = await llm.generate(system_prompt=_REVIEW_PROMPT, user_prompt=f"Achado: {payload}\nTrecho: {(item_content or '')[:500]}")
        else:
            text = str(await llm.agenerate(prompt=prompt, context=f"Achado: {payload}", max_tokens=120))  # type: ignore[attr-defined]
        import json as _json

        raw = text.strip() if isinstance(text, str) else str(text)
        start = raw.find("{")
        end = raw.rfind("}")
        data = _json.loads(raw[start : end + 1]) if start != -1 and end != -1 else {}
        delta = float(data.get("delta", 0)) if isinstance(data.get("delta"), (int, float)) else 0
        delta = max(-0.06, min(0.06, delta))
        note = str(data.get("note", "")).strip()[:120] if data.get("note") else ""
        suggestion.confidence = max(0.0, min(1.0, float(suggestion.confidence) + delta))
        if note:
            suggestion.reason = f"{suggestion.reason} · 2ª opinião: {note}"
        return suggestion
    except Exception as exc:  # noqa: BLE001 — consultivo, nunca quebra
        from app.services.privacy import PrivacyPolicyError

        if isinstance(exc, PrivacyPolicyError):
            logger.info(
                "privacy.decision document_id=- classification=%s provider=%s decision=blocked",
                classification or "unclassified",
                "policy",
            )
        else:
            logger.debug("reviewer.second_opinion.skip: %s", type(exc).__name__)
        return suggestion
