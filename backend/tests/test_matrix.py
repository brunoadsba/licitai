"""
Testes da montagem da matriz de conformidade (RF03).
"""

from app.services.comparator.matrix import montar_matriz


REGRAS = [
    {"id": "vigencia", "rotulo": "Vigência"},
    {"id": "garantia", "rotulo": "Garantia"},
]

FORNECEDORES = [
    {"id": "forn-a", "nome": "Empresa A"},
    {"id": "forn-b", "nome": "Empresa B"},
]

RESULTADOS = [
    {"regra_id": "vigencia", "fornecedor_id": "forn-a", "status": "ok",
     "motivo": "OK", "valor_tr": "90", "valor_proposta": "90"},
    {"regra_id": "vigencia", "fornecedor_id": "forn-b", "status": "falha",
     "motivo": "Diverge", "valor_tr": "90", "valor_proposta": "60"},
    {"regra_id": "garantia", "fornecedor_id": "forn-a", "status": "ok",
     "motivo": "OK", "valor_tr": None, "valor_proposta": None},
]


def test_matriz_tem_linhas_e_colunas_corretas():
    matriz = montar_matriz(
        comparacao_id="cmp-1",
        tr_document_id="tr-1",
        status="completed",
        regras=REGRAS,
        fornecedores=FORNECEDORES,
        resultados=RESULTADOS,
    )
    assert len(matriz["linhas"]) == 2
    assert [f["nome"] for f in matriz["fornecedores"]] == [
        "Empresa A", "Empresa B"
    ]
    assert matriz["regras"] == ["vigencia", "garantia"]


def test_matriz_status_por_celula():
    matriz = montar_matriz(
        comparacao_id="cmp-1",
        tr_document_id="tr-1",
        status="completed",
        regras=REGRAS,
        fornecedores=FORNECEDORES,
        resultados=RESULTADOS,
    )
    linha_vigencia = matriz["linhas"][0]
    celulas = {
        c["fornecedor_id"]: c for c in linha_vigencia["celulas"]
    }
    assert celulas["forn-a"]["status"] == "ok"
    assert celulas["forn-b"]["status"] == "falha"
    assert celulas["forn-b"]["valor_tr"] == "90"
    assert celulas["forn-b"]["valor_proposta"] == "60"


def test_matriz_regra_sem_resultado_vira_atencao():
    resultados = RESULTADOS[:-1]  # remove garantia/forn-a
    matriz = montar_matriz(
        comparacao_id="cmp-1",
        tr_document_id="tr-1",
        status="completed",
        regras=REGRAS,
        fornecedores=FORNECEDORES,
        resultados=resultados,
    )
    linha_garantia = matriz["linhas"][1]
    for celula in linha_garantia["celulas"]:
        assert celula["status"] == "atencao"
