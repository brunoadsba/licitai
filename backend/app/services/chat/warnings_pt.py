"""
Mensagens de aviso do Copiloto em português do Brasil.

`reason` interno é sempre um slug estável; prosa do LLM (qualquer idioma)
nunca é repassada à UI.
"""

from __future__ import annotations

import re

KNOWN_REASON_SLUGS = frozenset(
    {
        "recusa-llm",
        "sem-citacao",
        "sem-fontes",
        "fora-escopo",
        "resposta-invalida",
        "resposta-vazia",
        "source-id-inexistente",
        "falha-llm",
    }
)

REFUSAL_MESSAGE = (
    "Não encontrei fontes suficientes para responder essa pergunta com "
    "segurança. Reformule a pergunta ou pergunte sobre itens específicos "
    "do documento analisado."
)

FORA_ESCOPO_MESSAGE = (
    "Posso ajudar com este Termo de Referência e com licitações públicas. "
    "Reformule a pergunta nesse contexto — ou use uma das sugestões abaixo."
)

GREETING_MESSAGE = (
    "Olá! Posso ajudar com este Termo de Referência e com a legislação "
    "aplicável. Escolha uma sugestão ou pergunte com suas palavras."
)

FALHA_LLM_MESSAGE = (
    "Não foi possível processar sua pergunta agora. "
    "Tente novamente em instantes."
)

# Aviso amarelo na UI — None quando o corpo da mensagem já explica.
_WARNING_PT: dict[str, str | None] = {
    "fora-escopo": None,
    "sem-citacao": None,
    "sem-fontes": None,
    "resposta-invalida": None,
    "resposta-vazia": None,
    "source-id-inexistente": None,
    "falha-llm": None,
    "recusa-llm": None,
}

_CONTENT_PT: dict[str, str] = {
    "fora-escopo": FORA_ESCOPO_MESSAGE,
    "falha-llm": FALHA_LLM_MESSAGE,
}

_OUT_OF_SCOPE_RE = re.compile(
    r"("
    r"pertain|procurement|off[\s-]?topic|out of scope|"
    r"does not|not about|unrelated|"
    r"fora[\s-]?do[\s-]?escopo|fora[\s-]?escopo|"
    r"n[aã]o\s+(se\s+)?(refere|trata|diz\s+respeito)|"
    r"assunto\s+n[aã]o\s+relacionado"
    r")",
    re.IGNORECASE,
)

_GREETING_RE = re.compile(
    r"^\s*("
    r"oi|ol[aá]|ola|hey|hello|hi|"
    r"bom\s+dia|boa\s+tarde|boa\s+noite|"
    r"e\s*a[ií]|eai|tudo\s+bem\??|td\s+bem\??"
    r")\s*[!.?]*\s*$",
    re.IGNORECASE,
)


def is_greeting(text: str | None) -> bool:
    """Detecta cumprimento curto (ex.: oi, olá, bom dia)."""
    if not text:
        return False
    return bool(_GREETING_RE.match(text.strip()))


def normalize_reason(raw: str | None) -> str:
    """Converte reason do LLM (slug ou prosa) em slug conhecido."""
    if raw is None:
        return "recusa-llm"
    text = str(raw).strip()
    if not text:
        return "recusa-llm"
    lowered = text.lower()
    if lowered in KNOWN_REASON_SLUGS:
        return lowered
    if _OUT_OF_SCOPE_RE.search(text):
        return "fora-escopo"
    return "recusa-llm"


def refusal_content_pt(reason_slug: str) -> str:
    """Texto principal da mensagem de recusa em PT-BR."""
    return _CONTENT_PT.get(reason_slug, REFUSAL_MESSAGE)


def warning_message_pt(reason: str | None) -> str | None:
    """
    Texto de aviso para a UI (PT-BR).

    Aceita slug ou prosa; nunca devolve o texto bruto do LLM.
    """
    slug = normalize_reason(reason)
    return _WARNING_PT.get(slug)
