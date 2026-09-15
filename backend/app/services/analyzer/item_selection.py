"""Seleção de itens para análise (orçamento LLM) — extraído de `engine.py`."""

import re

from app.models.document import DocumentItem
from app.services.parser.detection_substantive import is_substantive_content

# Prefixos de numeração priorizados no orçamento (Art. 6º / cláusulas críticas)
_PRIORITY_SECTION_PREFIXES = ("1", "3", "4", "5", "7")


def _item_is_substantive(item: DocumentItem) -> bool:
    return is_substantive_content(
        content=item.content or "",
        title=item.title,
        item_number=item.item_number,
        item_type=item.item_type,
    )


def _section_root(item_number: str) -> str:
    """Raiz numérica da seção (ex.: '4.3.1' → '4', '01' → '1', '4.8-1' → '4')."""
    raw = (item_number or "").strip()
    # Sufixo de desambiguação do estruturador (ex.: a-1, 4.8-1)
    raw = re.sub(r"-\d+$", "", raw)
    first = raw.split(".", 1)[0]
    digits = "".join(ch for ch in first if ch.isdigit())
    if not digits:
        return raw
    return str(int(digits))


def _priority_rank(item: DocumentItem) -> tuple[int, int]:
    """
    Ordenação para orçamento limitado: seções críticas primeiro,
    depois ordem original do documento.
    """
    root = _section_root(item.item_number)
    if root in _PRIORITY_SECTION_PREFIXES:
        return (0, _PRIORITY_SECTION_PREFIXES.index(root))
    return (1, 99)


def select_items_for_analysis(
    items: list[DocumentItem],
    max_items: int | None = None,
) -> tuple[list[DocumentItem], list[DocumentItem], bool]:
    """
    Filtra títulos/subtópicos e aplica teto de orçamento nas cláusulas reais.

    Returns:
        (work_items, skipped_headings, budget_truncated)
    """
    substantive = [i for i in items if _item_is_substantive(i)]
    headings = [i for i in items if not _item_is_substantive(i)]

    budget_truncated = False
    if max_items is not None and max_items > 0 and len(substantive) > max_items:
        # Preservar ordem do documento, mas priorizar seções críticas
        ranked = sorted(
            enumerate(substantive),
            key=lambda pair: (_priority_rank(pair[1]), pair[0]),
        )
        chosen_idx = {idx for idx, _ in ranked[:max_items]}
        # Manter ordem relativa do documento entre os escolhidos
        substantive = [item for idx, item in enumerate(substantive) if idx in chosen_idx]
        budget_truncated = True

    return substantive, headings, budget_truncated
