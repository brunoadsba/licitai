"""
Checklist canônico do Art. 6º, XXIII, alíneas a–j da Lei 14.133/2021.

Fonte: backend/data/laws/lei-14133-2021.txt (texto oficial do inciso XXIII).
Toda UI/prompt/validador deve importar daqui — nunca duplicar a taxonomia.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Art6Element:
    key: str
    alinea: str
    title: str
    description: str
    keywords: tuple[str, ...]


ART6_XXIII_ELEMENTS: tuple[Art6Element, ...] = (
    Art6Element(
        key="objeto",
        alinea="a",
        title="Definição do objeto",
        description=(
            "definição do objeto, incluídos sua natureza, os quantitativos, "
            "o prazo do contrato e, se for o caso, a possibilidade de sua prorrogação"
        ),
        keywords=("objeto", "natureza", "quantitativo", "prazo do contrato"),
    ),
    Art6Element(
        key="fundamentacao",
        alinea="b",
        title="Fundamentação da contratação",
        description=(
            "fundamentação da contratação, que consiste na referência aos estudos "
            "técnicos preliminares correspondentes ou extrato das partes não sigilosas"
        ),
        keywords=("fundamentacao", "fundamentação", "estudo tecnico", "estudos técnicos", "justificativa"),
    ),
    Art6Element(
        key="descricao_solucao",
        alinea="c",
        title="Descrição da solução como um todo",
        description=(
            "descrição da solução como um todo, considerado todo o ciclo de vida do objeto"
        ),
        keywords=("solucao como um todo", "solução como um todo", "ciclo de vida"),
    ),
    Art6Element(
        key="requisitos",
        alinea="d",
        title="Requisitos da contratação",
        description="requisitos da contratação",
        keywords=("requisitos", "especificac", "requisitos da contratacao"),
    ),
    Art6Element(
        key="modelo_execucao",
        alinea="e",
        title="Modelo de execução do objeto",
        description=(
            "modelo de execução do objeto, que consiste na definição de como o contrato "
            "deverá produzir os resultados pretendidos desde o seu início até o seu encerramento"
        ),
        keywords=("modelo de execucao", "modelo de execução", "execucao do objeto", "execução do objeto"),
    ),
    Art6Element(
        key="modelo_gestao",
        alinea="f",
        title="Modelo de gestão do contrato",
        description=(
            "modelo de gestão do contrato, que descreve como a execução do objeto "
            "será acompanhada e fiscalizada pelo órgão ou entidade"
        ),
        keywords=("modelo de gestao", "modelo de gestão", "fiscalizacao", "fiscalização"),
    ),
    Art6Element(
        key="criterios_medicao_pagamento",
        alinea="g",
        title="Critérios de medição e de pagamento",
        description="critérios de medição e de pagamento",
        keywords=("medicao", "medição", "pagamento", "criterios de medicao"),
    ),
    Art6Element(
        key="selecao_fornecedor",
        alinea="h",
        title="Forma e critérios de seleção do fornecedor",
        description="forma e critérios de seleção do fornecedor",
        keywords=("selecao", "seleção", "criterio de julgamento", "critério de julgamento", "fornecedor"),
    ),
    Art6Element(
        key="estimativa_valor",
        alinea="i",
        title="Estimativas do valor da contratação",
        description=(
            "estimativas do valor da contratação, acompanhadas dos preços unitários "
            "referenciais, das memórias de cálculo e dos documentos que lhes dão suporte"
        ),
        keywords=("estimativa", "valor da contratacao", "precos", "preços", "orcament"),
    ),
    Art6Element(
        key="adequacao_orcamentaria",
        alinea="j",
        title="Adequação orçamentária",
        description="adequação orçamentária",
        keywords=("adequacao orcamentaria", "adequação orçamentária", "dotacao", "dotação", "orcamentaria"),
    ),
)


def art6_keys() -> list[str]:
    return [e.key for e in ART6_XXIII_ELEMENTS]


def art6_checklist_prompt_block() -> str:
    """Bloco pronto para system prompts."""
    lines = [
        "CHECKLIST OBRIGATÓRIO DO TR — Art. 6º, XXIII, alíneas a–j da Lei 14.133/2021:",
        "Sinalize ausência de qualquer alínea. NÃO invente elementos fora desta lista.",
        "",
    ]
    for e in ART6_XXIII_ELEMENTS:
        lines.append(f"- ({e.alinea}) {e.title}: {e.description}")
    return "\n".join(lines)
