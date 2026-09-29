"""Escolhe quais fontes do Copiloto cabem no prompt.

A lei não pode expulsar o TR: pergunta sobre objeto, prazo ou correção
precisa ver o item e a correção, não só os cinco chunks jurídicos.
"""

from __future__ import annotations

import re

from app.schemas.chat import ChatCitation

_STOP = frozenset(
    """
    a o os as de da do das dos e em no na nos nas um uma para por com sem
    que ha há este esta neste nesta esse essa isso isto seu sua
    qual quais como onde quando mais sao são ser foi tem há
    sobre pelo pela aos às as
    """.split()
)

_SEV = {
    "critico": 5,
    "crítico": 5,
    "alto": 4,
    "medio": 3,
    "médio": 3,
    "baixo": 2,
    "info": 1,
}

_URGENT_RE = re.compile(r"urgent|priorit|mais grav|cr[ií]tic", re.IGNORECASE)
_ART6_RE = re.compile(r"art\.?\s*6", re.IGNORECASE)
_OBJETO_RE = re.compile(r"\bobjeto\b", re.IGNORECASE)


def tokens(text: str) -> set[str]:
    words = re.findall(r"[0-9a-záàâãéêíóôõúç]+", (text or "").lower())
    return {w for w in words if w not in _STOP and (len(w) > 2 or w.isdigit())}


def lexical_score(query: str, text: str) -> int:
    q = tokens(query)
    if not q:
        return 0
    return len(q & tokens(text))


def is_urgent_query(query: str) -> bool:
    return bool(_URGENT_RE.search(query or ""))


def is_art6_query(query: str) -> bool:
    return bool(_ART6_RE.search(query or ""))


def is_objeto_query(query: str) -> bool:
    return bool(_OBJETO_RE.search(query or ""))


def severity_rank(reference: str) -> int:
    ref = (reference or "").lower()
    for name, rank in _SEV.items():
        if name in ref:
            return rank
    return 0


def _blob(fonte: ChatCitation) -> str:
    return f"{fonte.title} {fonte.snippet} {fonte.reference}"


def _dedupe(fontes: list[ChatCitation]) -> list[ChatCitation]:
    vistos: set[str] = set()
    saida: list[ChatCitation] = []
    for fonte in fontes:
        chave = fonte.source_id or f"{fonte.type}:{fonte.reference}"
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(fonte)
    return saida


def compose_sources(
    query: str,
    legais: list[ChatCitation],
    analysis: list[ChatCitation],
    corrections: list[ChatCitation],
    items: list[ChatCitation],
    max_n: int,
) -> list[ChatCitation]:
    """Monta o pacote final: parecer, trechos do TR e lei, sem estourar o teto."""
    analysis = analysis[:1]
    legais = legais[:3]
    dossier = _rank_dossier(query, corrections, items)
    room = max_n - len(analysis) - len(legais)
    need = min(3, len(dossier))
    if room < need:
        legais = legais[: max(0, len(legais) - (need - room))]
        room = max_n - len(analysis) - len(legais)
    room = max(0, room)
    return _dedupe(analysis + dossier[:room] + legais)[:max_n]


def _rank_dossier(
    query: str,
    corrections: list[ChatCitation],
    items: list[ChatCitation],
) -> list[ChatCitation]:
    dossier = list(corrections) + list(items)
    if is_urgent_query(query):
        corrs = sorted(
            [f for f in dossier if f.type == "correction"],
            key=lambda f: severity_rank(f.reference),
            reverse=True,
        )
        resto = [f for f in dossier if f.type != "correction"]
        return corrs + resto

    def chave(fonte: ChatCitation) -> tuple[int, int]:
        return (lexical_score(query, _blob(fonte)), severity_rank(fonte.reference))

    ranked = sorted(dossier, key=chave, reverse=True)
    positivos = [f for f in ranked if lexical_score(query, _blob(f)) > 0]
    return positivos or ranked


def select_for_answer(query: str, fontes: list[ChatCitation]) -> list[ChatCitation]:
    """Fontes do TR/análise que sustentam uma resposta quando o modelo recusa."""
    dossier = [f for f in fontes if f.type in {"analysis", "correction", "document_item"}]
    if not dossier:
        return []
    if is_urgent_query(query):
        corrs = [f for f in dossier if f.type == "correction"]
        corrs.sort(key=lambda f: severity_rank(f.reference), reverse=True)
        return (corrs or dossier)[:3]
    ranked = sorted(
        dossier, key=lambda f: lexical_score(query, _blob(f)), reverse=True
    )
    if lexical_score(query, _blob(ranked[0])) <= 0:
        if is_art6_query(query) or is_objeto_query(query):
            parecer = [f for f in dossier if f.type == "analysis"]
            return parecer[:1]
        return []
    return [f for f in ranked if lexical_score(query, _blob(f)) > 0][:4]
