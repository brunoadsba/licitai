"""
Validador de completude do TR gerado — Art. 6º, XXIII, alíneas a–j.
"""

from __future__ import annotations

import re
import unicodedata

from app.services.legal.art6_xxiii import ART6_XXIII_ELEMENTS


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def validate_tr_completeness(secoes: list[dict]) -> list[str]:
    if not secoes:
        return [e.key for e in ART6_XXIII_ELEMENTS]
    titulos = [
        _norm(s.get("title", "") + " " + s.get("item_number", "") + " " + (s.get("content") or "")[:200])
        for s in secoes
    ]
    faltantes: list[str] = []
    for elem in ART6_XXIII_ELEMENTS:
        keywords = [_norm(k) for k in elem.keywords]
        found = any(any(kw in t for kw in keywords) for t in titulos)
        if not found:
            faltantes.append(elem.key)
    return faltantes


FALLBACK_POR_ELEMENTO = {
    "objeto": {
        "item_number": "1.0",
        "title": "DA DEFINIÇÃO DO OBJETO",
        "content": (
            "Definição do objeto, natureza, quantitativos, prazo do contrato "
            "e possibilidade de prorrogação (Art. 6º, XXIII, a)."
        ),
    },
    "fundamentacao": {
        "item_number": "2.0",
        "title": "DA FUNDAMENTAÇÃO DA CONTRATAÇÃO",
        "content": (
            "Fundamentação com referência aos estudos técnicos preliminares "
            "correspondentes (Art. 6º, XXIII, b)."
        ),
    },
    "descricao_solucao": {
        "item_number": "3.0",
        "title": "DA DESCRIÇÃO DA SOLUÇÃO COMO UM TODO",
        "content": (
            "Descrição da solução considerando o ciclo de vida do objeto "
            "(Art. 6º, XXIII, c)."
        ),
    },
    "requisitos": {
        "item_number": "4.0",
        "title": "DOS REQUISITOS DA CONTRATAÇÃO",
        "content": "Requisitos da contratação (Art. 6º, XXIII, d).",
    },
    "modelo_execucao": {
        "item_number": "5.0",
        "title": "DO MODELO DE EXECUÇÃO DO OBJETO",
        "content": (
            "Modelo de execução do objeto desde o início até o encerramento "
            "(Art. 6º, XXIII, e)."
        ),
    },
    "modelo_gestao": {
        "item_number": "6.0",
        "title": "DO MODELO DE GESTÃO DO CONTRATO",
        "content": (
            "Modelo de gestão e fiscalização pelo órgão ou entidade "
            "(Art. 6º, XXIII, f)."
        ),
    },
    "criterios_medicao_pagamento": {
        "item_number": "7.0",
        "title": "DOS CRITÉRIOS DE MEDIÇÃO E DE PAGAMENTO",
        "content": "Critérios de medição e de pagamento (Art. 6º, XXIII, g).",
    },
    "selecao_fornecedor": {
        "item_number": "8.0",
        "title": "DA FORMA E CRITÉRIOS DE SELEÇÃO DO FORNECEDOR",
        "content": "Forma e critérios de seleção do fornecedor (Art. 6º, XXIII, h).",
    },
    "estimativa_valor": {
        "item_number": "9.0",
        "title": "DAS ESTIMATIVAS DO VALOR DA CONTRATAÇÃO",
        "content": (
            "Estimativas do valor com preços unitários referenciais e memórias "
            "de cálculo (Art. 6º, XXIII, i)."
        ),
    },
    "adequacao_orcamentaria": {
        "item_number": "10.0",
        "title": "DA ADEQUAÇÃO ORÇAMENTÁRIA",
        "content": "Adequação orçamentária (Art. 6º, XXIII, j).",
    },
}

# Compat: nomes antigos usados em testes/golden legados
ELEMENTOS_ART6 = [
    (e.key, list(e.keywords)) for e in ART6_XXIII_ELEMENTS
]
