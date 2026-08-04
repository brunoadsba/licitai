"""
Testes do comparador determinístico TR × Propostas (RF03).
"""

import asyncio

import pytest

from app.services.comparator.comparator import (
    comparar_regra,
    comparar,
    STATUS_OK,
    STATUS_FALHA,
    STATUS_ATENCAO,
)


def regra_numerica():
    return {
        "id": "vigencia",
        "rotulo": "Vigência",
        "tipo": "numero_inteiro",
        "ancora": "vigência",
    }


def test_numerico_igual_ok():
    resultado = comparar_regra(regra_numerica(), 90, 90)
    assert resultado["status"] == STATUS_OK


def test_numerico_int_float_misturados_ok():
    """Int no TR e float na proposta (90 vs 90.0) não devem divergir."""
    resultado = comparar_regra(regra_numerica(), 90, 90.0)
    assert resultado["status"] == STATUS_OK
    resultado = comparar_regra(regra_numerica(), 90.0, 90)
    assert resultado["status"] == STATUS_OK


def test_numerico_decimal_mantem_diferenca():
    """Valores decimais distintos não podem colidir após normalização."""
    regra = {"id": "reajuste", "rotulo": "Reajuste", "tipo": "percentual"}
    assert comparar_regra(regra, 12.34, 123.4)["status"] == STATUS_FALHA


def test_numerico_string_br_normalizada():
    """String pt-BR (milhar/ponto, decimal/vírgula) é normalizada corretamente."""
    regra = {"id": "valor", "rotulo": "Valor", "tipo": "monetario"}
    assert comparar_regra(regra, "1.500,00", "1500.00")["status"] == STATUS_OK
    assert comparar_regra(regra, "1.500,00", "1600.00")["status"] == STATUS_FALHA


def test_numerico_diferente_falha():
    resultado = comparar_regra(regra_numerica(), 90, 60)
    assert resultado["status"] == STATUS_FALHA
    assert "diverge" in resultado["motivo"]


def test_numerico_proposta_ausente_falha():
    resultado = comparar_regra(regra_numerica(), 90, None)
    assert resultado["status"] == STATUS_FALHA
    assert "não localizado" in resultado["motivo"]


def test_numerico_tr_ausente_atencao():
    resultado = comparar_regra(regra_numerica(), None, 90)
    assert resultado["status"] == STATUS_ATENCAO


def test_booleano_presente_ok():
    regra = {
        "id": "garantia",
        "rotulo": "Garantia",
        "tipo": "booleano",
        "palavras_chave": ["garantia"],
    }
    assert comparar_regra(regra, True, True)["status"] == STATUS_OK


def test_booleano_ausente_falha():
    regra = {
        "id": "garantia",
        "rotulo": "Garantia",
        "tipo": "booleano",
        "palavras_chave": ["garantia"],
    }
    assert comparar_regra(regra, True, False)["status"] == STATUS_FALHA


def test_legal_ok_e_falha():
    regra = {
        "id": "lei",
        "rotulo": "Lei",
        "tipo": "legal",
        "regex": r"14\.133/2021",
    }
    assert comparar_regra(regra, True, True)["status"] == STATUS_OK
    assert comparar_regra(regra, True, False)["status"] == STATUS_FALHA


def test_comparar_multiplicidade():
    regras = [regra_numerica()]
    itens_tr = [
        {
            "item_number": "1",
            "title": "Vigência",
            "content": "vigência de 90 dias",
        }
    ]
    propostas = [
        {
            "fornecedor_id": "fornecedor-a",
            "itens": [
                {"item_number": "1", "title": "Vigência",
                 "content": "vigência de 90 dias"}
            ],
        },
        {
            "fornecedor_id": "fornecedor-b",
            "itens": [
                {"item_number": "1", "title": "Vigência",
                 "content": "vigência de 60 dias"}
            ],
        },
    ]

    resultados = asyncio.run(comparar(regras, itens_tr, propostas))

    assert len(resultados) == 2
    por_fornecedor = {r["fornecedor_id"]: r for r in resultados}
    assert por_fornecedor["fornecedor-a"]["status"] == STATUS_OK
    assert por_fornecedor["fornecedor-b"]["status"] == STATUS_FALHA


def test_data_igual_ok():
    regra = {"id": "entrega", "rotulo": "Entrega", "tipo": "data"}
    assert comparar_regra(regra, "2026-12-15", "2026-12-15")["status"] == STATUS_OK


def test_data_diferente_falha():
    regra = {"id": "entrega", "rotulo": "Entrega", "tipo": "data"}
    assert comparar_regra(regra, "2026-12-15", "2026-12-20")["status"] == STATUS_FALHA


def test_percentual_igual_ok_e_diferente_falha():
    regra = {"id": "reajuste", "rotulo": "Reajuste", "tipo": "percentual"}
    assert comparar_regra(regra, 4.5, 4.5)["status"] == STATUS_OK
    assert comparar_regra(regra, 4.5, 3.0)["status"] == STATUS_FALHA


def test_monetario_igual_ok():
    regra = {"id": "valor", "rotulo": "Valor", "tipo": "monetario"}
    assert comparar_regra(regra, 1500.0, 1500.0)["status"] == STATUS_OK
    assert comparar_regra(regra, 1500.0, 1600.0)["status"] == STATUS_FALHA
