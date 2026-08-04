"""
Construção da matriz de conformidade: regras × fornecedores.

A matriz organiza os resultados de uma comparação em linhas (regras) e
colunas (fornecedores), permitindo visualizar a conformidade de cada
proposta em relação ao TR.
"""

import logging

logger = logging.getLogger(__name__)


def montar_matriz(
    comparacao_id: str,
    tr_document_id: str,
    status: str,
    regras: list[dict],
    fornecedores: list[dict],
    resultados: list[dict],
) -> dict:
    """
    Monta a matriz de conformidade.

    Args:
        comparacao_id: id da comparação.
        tr_document_id: id do documento TR.
        status: status da comparação.
        regras: regras do molde (id, rotulo).
        fornecedores: lista de dicts {"id", "nome", ...}.
        resultados: lista de resultados (comparar()).

    Returns:
        Dict no formato do schema MatrizResponse.
    """
    # Índice de resultados: (regra_id, fornecedor_id) -> resultado
    index = {
        (r["regra_id"], str(r["fornecedor_id"])): r
        for r in resultados
    }

    linhas = []
    for regra in regras:
        celulas = []
        for fornecedor in fornecedores:
            fornec_id = str(fornecedor["id"])
            resultado = index.get((regra["id"], fornec_id))
            if resultado is None:
                celulas.append({
                    "fornecedor_id": fornec_id,
                    "status": "atencao",
                    "motivo": "Regra não avaliada para este fornecedor.",
                    "valor_tr": None,
                    "valor_proposta": None,
                })
            else:
                celulas.append({
                    "fornecedor_id": fornec_id,
                    "status": resultado["status"],
                    "motivo": resultado["motivo"],
                    "valor_tr": resultado["valor_tr"],
                    "valor_proposta": resultado["valor_proposta"],
                })
        linhas.append({
            "regra_id": regra["id"],
            "rotulo": regra.get("rotulo", regra["id"]),
            "celulas": celulas,
        })

    return {
        "comparacao_id": comparacao_id,
        "tr_document_id": tr_document_id,
        "status": status,
        "regras": [regra["id"] for regra in regras],
        "fornecedores": fornecedores,
        "linhas": linhas,
    }
