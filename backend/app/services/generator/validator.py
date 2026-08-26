import re

ELEMENTOS_ART6 = [
    ("objeto", ["objeto"]),
    ("justificativa", ["justificativa"]),
    ("especificacoes_tecnicas", ["especificac", "requisitos"]),
    ("modelo_execucao", ["modelo de execucao", "execucao do contrato", "execução"]),
    ("modelo_gestao", ["modelo de gestao", "gestão", "fiscalizacao", "fiscalização"]),
    ("criterios_medicao", ["criterios de medicao", "medição", "pagamento"]),
    ("estimativa_precos", ["estimativa", "precos", "preços", "orcamentaria", "orçamentária"]),
    ("garantia", ["garantia"]),
    ("infracoes_sancoes", ["infracoes", "infrações", "sancoes", "sanções"]),
    ("forma_selecao", ["forma de selecao", "seleção", "criterio de julgamento", "critério"]),
]


def _norm(s: str) -> str:
    import unicodedata

    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def validate_tr_completeness(secoes: list[dict]) -> list[str]:
    if not secoes:
        return [e[0] for e in ELEMENTOS_ART6]
    titulos = [_norm(s.get("title", "") + " " + s.get("item_number", "")) for s in secoes]
    faltantes: list[str] = []
    for key, keywords in ELEMENTOS_ART6:
        found = any(any(kw in t for kw in [_norm(k) for k in keywords]) for t in titulos)
        if not found:
            faltantes.append(key)
    return faltantes


FALLBACK_POR_ELEMENTO = {
    "objeto": {"item_number": "1.0", "title": "DO OBJETO", "content": "Objeto a definir conforme contratação."},
    "justificativa": {"item_number": "2.0", "title": "DA JUSTIFICATIVA DA CONTRATAÇÃO", "content": "Justificativa a complementar."},
    "especificacoes_tecnicas": {"item_number": "3.0", "title": "DAS ESPECIFICAÇÕES TÉCNICAS E REQUISITOS DA CONTRATAÇÃO", "content": "Requisitos mínimos a detalhar."},
    "modelo_execucao": {"item_number": "4.0", "title": "DO MODELO DE EXECUÇÃO DO CONTRATO", "content": "Modelo de execução a definir."},
    "modelo_gestao": {"item_number": "5.0", "title": "DO MODELO DE GESTÃO E FISCALIZAÇÃO CONTRATUAL", "content": "Fiscalização por comissão/fiscal designado."},
    "criterios_medicao": {"item_number": "6.0", "title": "DOS CRITÉRIOS DE MEDIÇÃO E PAGAMENTO", "content": "Pagamento por liquidação de nota fiscal."},
    "estimativa_precos": {"item_number": "7.0", "title": "DA ESTIMATIVA DE PREÇOS E ADEQUAÇÃO ORÇAMENTÁRIA", "content": "Estimativa a definir em pesquisa de mercado."},
    "garantia": {"item_number": "8.0", "title": "DA GARANTIA CONTRATUAL E ASSISTÊNCIA TÉCNICA", "content": "Garantia conforme art. 96 da Lei 14.133/2021."},
    "infracoes_sancoes": {"item_number": "9.0", "title": "DAS INFRAÇÕES E SANÇÕES ADMINISTRATIVAS", "content": "Regime dos arts. 155 e seguintes da Lei 14.133/2021."},
    "forma_selecao": {"item_number": "10.0", "title": "DA FORMA DE SELEÇÃO E CRITÉRIO DE JULGAMENTO", "content": "Seleção por licitação, critério a definir."},
}
