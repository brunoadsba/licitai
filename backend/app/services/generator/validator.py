"""
Validador de completude do TR gerado — Art. 6º, XXIII, alíneas a–j.

Regra (rumo a ≥90% cobertura estrutural mensurável):
1. Keyword no título/item_number → presente (preferencial).
2. Keyword "forte" (composta ou longa) no título+corpo → presente.
3. ≥2 keywords fracas no mesmo bloco seção → presente.
4. Caso contrário → faltante.
"""

from __future__ import annotations

import re
import unicodedata

from app.services.legal.art6_xxiii import ART6_XXIII_ELEMENTS

ART6_COVERAGE_TARGET = 0.90


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def _heading(secao: dict) -> str:
    return _norm(
        f"{secao.get('title', '')} {secao.get('item_number', '')}"
    )


def _body(secao: dict, limit: int = 500) -> str:
    return _norm((secao.get("content") or "")[:limit])


def _split_keywords(keywords: tuple[str, ...] | list[str]) -> tuple[list[str], list[str]]:
    kws = [_norm(k) for k in keywords if k]
    strong = [k for k in kws if (" " in k) or (len(k) >= 12)]
    weak = [k for k in kws if k not in strong]
    return strong, weak


def _element_present(elem, secoes: list[dict]) -> bool:
    strong, weak = _split_keywords(elem.keywords)
    all_kws = strong + weak

    for secao in secoes:
        heading = _heading(secao)
        if any(kw in heading for kw in all_kws):
            return True

    for secao in secoes:
        blob = f"{_heading(secao)} {_body(secao)}"
        if strong and any(kw in blob for kw in strong):
            return True
        weak_hits = sum(1 for kw in weak if kw in blob)
        if weak_hits >= 2:
            return True
    return False


def validate_tr_completeness(secoes: list[dict]) -> list[str]:
    if not secoes:
        return [e.key for e in ART6_XXIII_ELEMENTS]
    faltantes: list[str] = []
    for elem in ART6_XXIII_ELEMENTS:
        if not _element_present(elem, secoes):
            faltantes.append(elem.key)
    return faltantes


def art6_coverage_ratio(secoes: list[dict]) -> float:
    """Fraçao de alíneas a–j detectadas (0.0–1.0)."""
    total = len(ART6_XXIII_ELEMENTS)
    if total == 0:
        return 0.0
    missing = len(validate_tr_completeness(secoes))
    return round((total - missing) / total, 3)


def meets_art6_coverage_target(secoes: list[dict], target: float = ART6_COVERAGE_TARGET) -> bool:
    return art6_coverage_ratio(secoes) >= target


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


def build_contextual_fallback(
    key: str,
    *,
    objeto: str = "",
    justificativa: str = "",
    valor_txt: str = "A definir",
    prazo_meses: int = 12,
    criterio: str = "menor preço",
    tipo_nome: str = "contratação",
) -> dict | None:
    """Stub estrutural com dados do request (melhor que texto genérico vazio)."""
    base = FALLBACK_POR_ELEMENTO.get(key)
    if not base:
        return None
    out = {**base}
    obj = (objeto or "objeto da contratação").strip()
    just = (justificativa or "necessidade administrativa identificada").strip()
    extras = {
        "objeto": (
            f"O objeto da presente contratação consiste em: {obj}. "
            f"Prazo de vigência estimado: {prazo_meses} meses (Art. 6º, XXIII, a)."
        ),
        "fundamentacao": (
            f"A contratação fundamenta-se na seguinte necessidade: {just}. "
            "Deve ser confrontada com os Estudos Técnicos Preliminares correspondentes "
            "(Art. 6º, XXIII, b)."
        ),
        "descricao_solucao": (
            f"A solução como um todo abrange o ciclo de vida de «{obj}», "
            "da contratação ao encerramento/desfazimento (Art. 6º, XXIII, c)."
        ),
        "requisitos": (
            f"Os requisitos da contratação de {tipo_nome} relativos a «{obj}» "
            "deverão observar especificações técnicas, legais e de sustentabilidade "
            "aplicáveis (Art. 6º, XXIII, d)."
        ),
        "modelo_execucao": (
            f"O modelo de execução define como «{obj}» produzirá os resultados "
            f"ao longo de {prazo_meses} meses, do início ao encerramento "
            "(Art. 6º, XXIII, e)."
        ),
        "modelo_gestao": (
            "A gestão e fiscalização do contrato serão exercidas por fiscal/comissão "
            "designada pela CODEBA, com registro de ocorrências (Art. 6º, XXIII, f)."
        ),
        "criterios_medicao_pagamento": (
            "Os critérios de medição e pagamento observarão aceites parciais/totais "
            "e liquidação mediante nota fiscal (Art. 6º, XXIII, g)."
        ),
        "selecao_fornecedor": (
            f"A seleção do fornecedor observará o critério de {criterio}, "
            "com habilitação conforme legislação aplicável (Art. 6º, XXIII, h)."
        ),
        "estimativa_valor": (
            f"Estimativa do valor da contratação: {valor_txt}, "
            "acompanhada de pesquisa/memória de cálculo quando disponível "
            "(Art. 6º, XXIII, i)."
        ),
        "adequacao_orcamentaria": (
            f"A despesa estimada ({valor_txt}) deverá observar adequação orçamentária "
            "e disponibilidade de créditos (Art. 6º, XXIII, j)."
        ),
    }
    if key in extras:
        out["content"] = extras[key]
    return out


# Compat: nomes antigos usados em testes/golden legados
ELEMENTOS_ART6 = [
    (e.key, list(e.keywords)) for e in ART6_XXIII_ELEMENTS
]
