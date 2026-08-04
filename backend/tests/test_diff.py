"""
Testes do diff entre versões de TR (RAG Fase 4.3).

Cobre a classificação por item_number: inalterado, alterado, adicionado,
removido, além da ordenação natural e do resumo.
"""

import pytest

from app.services.comparator.diff import diff_terms, resumir_diffs


def _item(numero: str, conteudo: str = "texto padrão") -> dict:
    return {"item_number": numero, "title": f"Título {numero}", "content": conteudo}


def test_diff_identifica_inalterado():
    antigo = [_item("1"), _item("2")]
    novo = [_item("1"), _item("2")]
    diffs = diff_terms(antigo, novo)

    assert {d.status for d in diffs} == {"inalterado"}
    assert len(diffs) == 2


def test_diff_identifica_alterado():
    antigo = [_item("1", "valor antigo do item")]
    novo = [_item("1", "novo conteúdo completamente diferente")]
    diffs = diff_terms(antigo, novo)

    assert diffs[0].status == "alterado"
    assert diffs[0].conteudo_antes == "valor antigo do item"
    assert diffs[0].conteudo_depois == "novo conteúdo completamente diferente"


def test_diff_identifica_adicionado_e_removido():
    antigo = [_item("1"), _item("3")]
    novo = [_item("1"), _item("2")]
    diffs = diff_terms(antigo, novo)

    statuses = {d.item_number: d.status for d in diffs}
    assert statuses["2"] == "adicionado"
    assert statuses["3"] == "removido"
    assert statuses["1"] == "inalterado"


def test_diff_ordena_naturalmente():
    antigo = [_item("10"), _item("2"), _item("1.1")]
    novo = [_item("10"), _item("2"), _item("1.1")]
    diffs = diff_terms(antigo, novo)

    assert [d.item_number for d in diffs] == ["1.1", "2", "10"]


def test_diff_minima_mudanca_nao_e_alterado():
    """Pequena mudança no texto mantém o item como inalterado (limiar 0.8)."""
    antigo = [_item("1", "exigência de garantia de execução contratual")]
    novo = [_item("1", "exigência de garantia de execução contratual e manutenção")]
    diffs = diff_terms(antigo, novo)

    assert diffs[0].status == "inalterado"


def test_resumir_diffs_contabiliza():
    antigo = [_item("1", "a"), _item("2", "b"), _item("3", "c")]
    novo = [_item("1", "a"), _item("2", "xxxx totalmente novo"), _item("4", "d")]
    diffs = diff_terms(antigo, novo)
    resumo = resumir_diffs(diffs)

    assert resumo["inalterado"] == 1
    assert resumo["alterado"] == 1
    assert resumo["adicionado"] == 1
    assert resumo["removido"] == 1
    assert sum(resumo.values()) == len(diffs)
