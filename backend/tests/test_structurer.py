"""
Testes de regressão do estruturador de documentos.

Cobrem bugs em documentos padrão SEI, exclusão de SUMÁRIO/ÍNDICE
e classificação de conteúdo substantivo vs título puro.
"""

from app.services.parser.detection import is_substantive_content
from app.services.parser.structurer import structure_items


def test_secao_com_numero_em_linha_isolada():
    texto = """1.
O OBJETO
Texto do objeto."""

    items = structure_items(texto, pages=[])

    assert len(items) == 1
    assert items[0]["item_type"] == "section"
    assert items[0]["item_number"] == "1"
    assert items[0]["title"] == "O OBJETO"


def test_item_com_numero_em_linha_isolada():
    texto = """2.1.
A presente contratação justifica-se pela necessidade."""

    items = structure_items(texto, pages=[])

    assert len(items) == 1
    assert items[0]["item_type"] == "item"
    assert items[0]["item_number"] == "2.1"
    assert items[0]["title"].startswith("A presente contratação")


def test_dados_de_tabela_nao_viram_itens():
    texto = """4.2.1. A manutenção preventiva compreenderá:
[TABELA]
9.000 BTU | Gree | 1
12.000 BTU | Elgin | 5
[/TABELA]
4.2.2. A manutenção preventiva será mensalmente:"""

    items = structure_items(texto, pages=[])

    numeros = [it["item_number"] for it in items]
    assert "9.000" not in numeros
    assert "12.000" not in numeros
    assert items[0]["item_type"] == "subitem"
    assert items[1]["item_type"] == "table"
    assert items[2]["item_type"] == "subitem"


def test_numero_isolado_seguido_de_outro_numero_nao_combina():
    texto = """1.
2.
Item real."""

    items = structure_items(texto, pages=[])

    # "1." sem título não vira seção; "2." combina com o título real
    assert len(items) == 1
    assert items[0]["item_number"] == "2"
    assert items[0]["title"] == "Item real."
    assert not any(it["item_number"] == "1-1" for it in items)


def test_rodape_sei_nao_vira_secao():
    texto = """1.
Referência: Processo nº 50903.000054/2026-17
Conteúdo do documento."""

    items = structure_items(texto, pages=[])

    assert len(items) == 1
    assert items[0]["item_number"] != "1-1"


def test_estrutura_completa():
    texto = """1.
O OBJETO
1.1.
Contratação de empresa especializada.
1.2.
A contratação será por SRP.
2.
DA JUSTIFICATIVA
2.1.
A contratação justifica-se pela necessidade.
[TABELA]
9.000 BTU | Gree | 1
[/TABELA]
2.2.
Adicionalmente, visa cumprir a legislação."""

    items = structure_items(texto, pages=[])

    tipos = [it["item_type"] for it in items]
    numeros = [it["item_number"] for it in items]

    assert tipos == ["section", "item", "item", "section", "item", "table", "item"]
    assert numeros == ["1", "1.1", "1.2", "2", "2.1", "TAB-6", "2.2"]


def test_titulo_gerado_deterministicamente():
    texto = "[TÍTULO] Contratação especializada"
    first = structure_items(texto, pages=[])[0]
    second = structure_items(texto, pages=[])[0]
    first_number = first.get("item_number") or first.get("number")
    second_number = second.get("item_number") or second.get("number")
    assert first_number == second_number
    assert first_number.startswith("T-")


def test_alinea_letra_detectada():
    items = structure_items("a) Entrega em 30 dias", pages=[])
    item = items[0]
    tipo = item.get("item_type", item.get("type"))
    numero = item.get("item_number", item.get("number"))
    assert tipo == "subitem"
    assert numero == "a"


def test_item_romano_detectado():
    items = structure_items("I. DO OBJETO", pages=[])
    item = items[0]
    tipo = item.get("item_type", item.get("type"))
    numero = item.get("item_number", item.get("number"))
    assert tipo == "section"
    assert numero == "I"


def test_sumario_nao_gera_itens():
    """Linhas do SUMÁRIO não viram DocumentItem; o corpo do TR sim."""
    texto = """
HISTÓRICO DE REVISÕES
SUMÁRIO
01 – OBJETO DA CONTRATAÇÃO
02 – DESCRIÇÃO DA SOLUÇÃO DE TIC
03 – JUSTIFICATIVA PARA A CONTRATAÇÃO
4.1. Requisitos de Negócio
Termo de Referência / Projeto Básico 3 versão 2.0 (11776923)         SEI 50903.003322/2026-52 / pg. 1
4.8. Requisitos de Capacitação
05 – RESPONSABILIDADES
TERMO DE REFERÊNCIA OU PROJETO BÁSICO
1.
OBJETO DA CONTRATAÇÃO
1.1.
A presente contratação tem por objeto a prestação de serviços de telefonia
fixa corporativa, contemplando STFC integrado à solução de PABX em nuvem.
"""
    items = structure_items(texto, pages=[])
    numeros = [it["item_number"] for it in items]
    # Não deve haver "01", "02", "03", "4.8", "05" do sumário
    assert "01" not in numeros
    assert "02" not in numeros
    assert "03" not in numeros
    assert "4.1" not in numeros
    assert "4.8" not in numeros
    assert "05" not in numeros
    assert "1" in numeros
    assert "1.1" in numeros
    assert any(
        "telefonia" in it["content"].lower()
        for it in items
        if it["item_number"] == "1.1"
    )


def test_indice_nao_gera_itens():
    texto = """
ÍNDICE
1. Objeto
2. Justificativa
TERMO DE REFERÊNCIA
1. Objeto
A contratação visa a aquisição de materiais de escritório em quantidade
suficiente para atender as unidades administrativas durante doze meses.
"""
    items = structure_items(texto, pages=[])
    # Apenas o corpo (seção 1 com texto), não a linha do índice
    assert len(items) == 1
    assert items[0]["item_number"] == "1"
    assert "aquisição" in items[0]["content"].lower()


def test_sumario_sem_termo_referencia_nao_engole_corpo():
    """Corpo após SUMÁRIO sem linha TERMO DE REFERÊNCIA ainda é estruturado."""
    texto = """
SUMÁRIO
1. Objeto
2. Justificativa
1. Objeto
A contratação visa a aquisição de materiais de escritório em quantidade
suficiente para atender as unidades administrativas durante doze meses.
2. Justificativa
A demanda decorre da necessidade contínua de suprimentos administrativos
para as unidades da autarquia no exercício vigente.
"""
    items = structure_items(texto, pages=[])
    numeros = [it["item_number"] for it in items]
    assert "1" in numeros
    assert "2" in numeros
    assert any("aquisição" in it["content"].lower() for it in items)
    assert any("demanda" in it["content"].lower() for it in items)


def test_is_substantive_titulo_puro_falso():
    assert not is_substantive_content(
        "01 – OBJETO DA CONTRATAÇÃO",
        title="OBJETO DA CONTRATAÇÃO",
        item_number="01",
        item_type="section",
    )
    assert not is_substantive_content(
        "1. OBJETO DA CONTRATAÇÃO",
        title="OBJETO DA CONTRATAÇÃO",
        item_number="1",
        item_type="section",
    )


def test_is_substantive_clausula_real_verdadeiro():
    content = (
        "1.1. A presente contratação tem por objeto a prestação de serviços de "
        "telefonia fixa corporativa, contemplando STFC integrado à solução de "
        "PABX em nuvem durante a vigência contratual."
    )
    assert is_substantive_content(
        content,
        title="A presente contratação tem por objeto",
        item_number="1.1",
        item_type="item",
    )


def test_is_substantive_tabela_sempre_falso():
    assert not is_substantive_content(
        "Data | Versão | Descrição | Autor",
        title="Tabela",
        item_number="TAB-1",
        item_type="table",
    )
