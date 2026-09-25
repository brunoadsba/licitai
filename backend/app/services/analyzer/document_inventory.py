"""
Inventário determinístico de fatos do TR (prazo, quantitativo, prorrogação).

Uma passagem no texto de todos os itens — sem LLM. Usado no prompt do item
e no G4 para não acusar omissão do Art. 6º quando o fato já está no documento.
"""

from __future__ import annotations

import re
import unicodedata

# Sinônimos normalizados (sem acento) usados pelo G4 e pelo extractor.
FACT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "prazo": ("prazo", "vigencia", "meses", "contratual"),
    "prorrogacao": ("prorrogacao", "prorrogavel"),
    "quantitativo": ("quantitativo", "quantidade", "ramais", "unidades", "itens"),
}

# Sinais mais específicos para localizar o primeiro item que contém o fato.
_FACT_SIGNALS: dict[str, re.Pattern[str]] = {
    "prazo": re.compile(r"vigencia|prazo\s+(do\s+)?contrato|\d+\s+meses"),
    "prorrogacao": re.compile(r"prorroga"),
    "quantitativo": re.compile(
        r"ramais|quantitativ|quantidade|\d+\s+unidades|unidades\s+\d+"
    ),
}

_FACT_LABELS = {
    "prazo": "prazo",
    "quantitativo": "quantitativo",
    "prorrogacao": "prorrogação",
}
_FACT_ORDER = ("prazo", "quantitativo", "prorrogacao")


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def _mentions_any(norm: str, terms: tuple[str, ...]) -> bool:
    if not norm:
        return False
    for term in terms:
        if len(term) <= 4:
            if re.search(rf"\b{re.escape(term)}\b", norm):
                return True
        elif term in norm:
            return True
    return False


def claimed_canonical_facts(text: str) -> set[str]:
    """Fatos canônicos citados em problem/suggested (via sinônimos)."""
    norm = _normalize(text)
    return {fact for fact, syns in FACT_SYNONYMS.items() if _mentions_any(norm, syns)}


def fact_in_text(text: str, fact: str) -> bool:
    return _mentions_any(_normalize(text), FACT_SYNONYMS.get(fact, ()))


def build_inventory(items: list) -> dict[str, str]:
    """Primeiro item_number em que cada fato aparece. Itera o item, não o texto solto."""
    found: dict[str, str] = {}
    for item in items or []:
        if len(found) == len(_FACT_SIGNALS):
            break
        number = str(getattr(item, "item_number", "") or "").strip()
        content = _normalize(getattr(item, "content", "") or "")
        if not number or not content:
            continue
        for fact, pattern in _FACT_SIGNALS.items():
            if fact not in found and pattern.search(content):
                found[fact] = number
    return found


def format_document_facts(inventory: dict[str, str]) -> str:
    parts = [
        f"{_FACT_LABELS[key]} em {inventory[key]}"
        for key in _FACT_ORDER
        if key in inventory
    ]
    if not parts:
        return (
            "Nenhum fato de prazo, quantitativo ou prorrogação foi "
            "localizado automaticamente no TR."
        )
    return "Já no TR: " + "; ".join(parts) + "."
