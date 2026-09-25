"""Remove ruído interno da resposta do Copiloto (UUID, source_id, falha de agente)."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_SOURCE_ID_RE = re.compile(
    r"\b(?:legal|analysis|correction|doc):[^\s,;)]+",
    re.IGNORECASE,
)
_AGENT_FAIL_RE = re.compile(
    r"\b(?:juridico|tecnico|redacao|estrutural|orchestrator)"
    r":(?:failed|parse_error|ok_empty|skipped)\b",
    re.IGNORECASE,
)
_PARECER_FOOTER_RE = re.compile(
    r"\n(?:Rastro das correções:|Fontes do parecer:|Recuperações:).*$",
    re.IGNORECASE | re.DOTALL,
)


def strip_parecer_audit(text: str) -> str:
    """Corta o rodapé de IDs do parecer antes de mandar ao LLM."""
    if not text:
        return ""
    return _PARECER_FOOTER_RE.sub("", text).strip()


def sanitize_answer(text: str) -> str:
    """Limpa a resposta persistida: sem UUID, source_id nem falha de agente."""
    if not text:
        return ""
    cleaned = _SOURCE_ID_RE.sub("", text)
    cleaned = _AGENT_FAIL_RE.sub("", cleaned)
    cleaned = _UUID_RE.sub("", cleaned)
    cleaned = strip_parecer_audit(cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
