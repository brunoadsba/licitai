"""
Diff entre versões de Termos de Referência (RAG Fase 4.3).

Compara dois documentos TR (antigo e novo) por item_number, classificando
cada item como: inalterado, alterado, adicionado ou removido.
"""

import difflib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

LIMIAR_SIMILARIDADE = 0.8


@dataclass
class ItemDiff:
    """Diferença de um item entre duas versões do TR."""

    status: str  # inalterado | alterado | adicionado | removido
    item_number: str
    titulo: str
    conteudo_antes: str | None
    conteudo_depois: str | None


def _normalizar(texto: str | None) -> str:
    """Normaliza texto para comparação (minúsculas, colapsa espaços)."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto.strip().lower())


def _similaridade(a: str, b: str) -> float:
    """Similaridade de sequência entre dois textos (0..1)."""
    return difflib.SequenceMatcher(None, _normalizar(a), _normalizar(b)).ratio()


def _chave_ordenacao(item_number: str) -> list:
    """Ordena números de item naturalmente (1 < 1.1 < 2 < 10)."""
    return [int(p) if p.isdigit() else p for p in re.findall(r"\d+|\D+", item_number)]


def diff_terms(antigo: list[dict], novo: list[dict]) -> list[ItemDiff]:
    """
    Compara dois conjuntos de itens de documento (TR antigo vs novo).

    Args:
        antigo: itens do TR antigo (dicts com `item_number`, `title`, `content`).
        novo: itens do TR novo.

    Returns:
        Lista de ItemDiff ordenada por item_number.
    """
    por_numero_antigo = {i["item_number"]: i for i in antigo}
    por_numero_novo = {i["item_number"]: i for i in novo}

    diffs: list[ItemDiff] = []

    for numero, item in por_numero_antigo.items():
        novo_item = por_numero_novo.get(numero)
        if novo_item is None:
            diffs.append(ItemDiff(
                status="removido",
                item_number=numero,
                titulo=item.get("title") or "",
                conteudo_antes=item.get("content") or "",
                conteudo_depois=None,
            ))
            continue
        conteudo_antes = item.get("content") or ""
        conteudo_depois = novo_item.get("content") or ""
        status = (
            "inalterado"
            if _similaridade(conteudo_antes, conteudo_depois) >= LIMIAR_SIMILARIDADE
            else "alterado"
        )
        diffs.append(ItemDiff(
            status=status,
            item_number=numero,
            titulo=novo_item.get("title") or "",
            conteudo_antes=conteudo_antes,
            conteudo_depois=conteudo_depois,
        ))

    for numero, item in por_numero_novo.items():
        if numero not in por_numero_antigo:
            diffs.append(ItemDiff(
                status="adicionado",
                item_number=numero,
                titulo=item.get("title") or "",
                conteudo_antes=None,
                conteudo_depois=item.get("content") or "",
            ))

    diffs.sort(key=lambda d: _chave_ordenacao(d.item_number))
    return diffs


def resumir_diffs(diffs: list[ItemDiff]) -> dict[str, int]:
    """Conta itens por status (resumo do diff)."""
    total = {"inalterado": 0, "alterado": 0, "adicionado": 0, "removido": 0}
    for d in diffs:
        total[d.status] += 1
    return total
