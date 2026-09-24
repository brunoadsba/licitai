"""Termos de conteúdo vs ruído de citação (Lei 14.133, 2021, art.)."""

from __future__ import annotations

import re
import unicodedata

_STOPWORDS = frozenset({
    "de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sob", "sobre", "que", "os", "as", "o", "a",
    "um", "uma", "uns", "umas", "ao", "aos", "se", "como", "ou", "e", "sao",
    "art", "artigo", "inciso", "alinea", "paragrafo",
})

_LAW_NOISE = frozenset({
    "lei", "2021", "2016", "14133", "13303", "14", "133", "13", "303",
})


def fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn").lower()


def _tokens(query: str) -> list[str]:
    folded = re.sub(r"(?<=\d)\.(?=\d{3})", "", fold(query))
    return re.findall(r"[0-9A-Za-zÀ-ÿ]{2,}", folded)


def content_terms(query: str) -> list[str]:
    """Palavras e números úteis, sem stopword e sem citação da lei."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in _tokens(query):
        if raw in _STOPWORDS or raw in _LAW_NOISE:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out


def word_terms(query: str) -> list[str]:
    return [t for t in content_terms(query) if not t.isdigit()]


def number_terms(query: str) -> list[str]:
    return [t for t in content_terms(query) if t.isdigit() and len(t) >= 3]


def tsquery_atom(term: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z]", "", term)
    if not safe:
        return ""
    if len(safe) >= 5:
        return f"{safe}:*"
    return safe


def postgres_tsquery(query: str, mode: str) -> str:
    """AND dos termos de conteúdo (2+) ou OR. Prefixo :* em termos longos."""
    words = [tsquery_atom(t) for t in word_terms(query)]
    words = [w for w in words if w]
    nums = [tsquery_atom(t) for t in number_terms(query)]
    nums = [n for n in nums if n]
    if mode == "and" and len(words) >= 2:
        parts = words[:4]
        if nums:
            parts.append("(" + " | ".join(nums) + ")")
        return " & ".join(parts)
    atoms = words + nums
    return " | ".join(atoms) if atoms else "lei"
