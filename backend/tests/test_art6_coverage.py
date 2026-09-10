"""Testes da métrica Art. 6º coverage (≥90%) e validador endurecido."""

from __future__ import annotations

from app.services.analyzer.art6_status import build_art6_checklist, summarize_art6_coverage
from app.services.generator.validator import (
    ART6_COVERAGE_TARGET,
    art6_coverage_ratio,
    build_contextual_fallback,
    validate_tr_completeness,
)


def _secoes_completas() -> list[dict]:
    return [
        {"item_number": "1.0", "title": "DA DEFINIÇÃO DO OBJETO", "content": "x"},
        {"item_number": "2.0", "title": "DA FUNDAMENTAÇÃO DA CONTRATAÇÃO", "content": "x"},
        {
            "item_number": "3.0",
            "title": "DA DESCRIÇÃO DA SOLUÇÃO COMO UM TODO",
            "content": "x",
        },
        {"item_number": "4.0", "title": "DOS REQUISITOS DA CONTRATAÇÃO", "content": "x"},
        {"item_number": "5.0", "title": "DO MODELO DE EXECUÇÃO DO OBJETO", "content": "x"},
        {"item_number": "6.0", "title": "DO MODELO DE GESTÃO DO CONTRATO", "content": "x"},
        {
            "item_number": "7.0",
            "title": "DOS CRITÉRIOS DE MEDIÇÃO E DE PAGAMENTO",
            "content": "x",
        },
        {
            "item_number": "8.0",
            "title": "DA FORMA E CRITÉRIOS DE SELEÇÃO DO FORNECEDOR",
            "content": "x",
        },
        {
            "item_number": "9.0",
            "title": "DAS ESTIMATIVAS DO VALOR DA CONTRATAÇÃO",
            "content": "x",
        },
        {"item_number": "10.0", "title": "DA ADEQUAÇÃO ORÇAMENTÁRIA", "content": "x"},
    ]


def test_coverage_completa_atinge_100():
    secoes = _secoes_completas()
    assert validate_tr_completeness(secoes) == []
    assert art6_coverage_ratio(secoes) == 1.0


def test_coverage_9_de_10_atinge_meta():
    secoes = _secoes_completas()[:-1]  # sem adequação orçamentária
    assert art6_coverage_ratio(secoes) == 0.9
    assert art6_coverage_ratio(secoes) >= ART6_COVERAGE_TARGET


def test_mencao_incidental_pagamento_nao_marca_medicao():
    """'pagamento' solto no corpo sem título de medição não basta."""
    secoes = [
        {
            "item_number": "1.0",
            "title": "DA DEFINIÇÃO DO OBJETO",
            "content": "Objeto com pagamento antecipado vedado.",
        },
    ]
    faltantes = validate_tr_completeness(secoes)
    assert "criterios_medicao_pagamento" in faltantes
    assert "objeto" not in faltantes


def test_contextual_fallback_fecha_cobertura():
    secoes = [{"item_number": "1.0", "title": "INTRODUÇÃO", "content": "Sem checklist."}]
    for key in validate_tr_completeness(secoes):
        fb = build_contextual_fallback(
            key,
            objeto="aquisição de EPIs",
            justificativa="necessidade de proteção aos trabalhadores",
            valor_txt="R$ 10.000,00",
        )
        assert fb is not None
        secoes.append(fb)
    assert art6_coverage_ratio(secoes) == 1.0


def test_summarize_art6_coverage():
    class Item:
        def __init__(self, n, t, c=""):
            self.item_number = n
            self.title = t
            self.content = c

    items = [Item(s["item_number"], s["title"], s["content"]) for s in _secoes_completas()]
    checklist = build_art6_checklist(items)
    summary = summarize_art6_coverage(checklist)
    assert summary["art6_present"] == 10
    assert summary["art6_coverage"] == 1.0
    assert summary["art6_meets_target"] is True
