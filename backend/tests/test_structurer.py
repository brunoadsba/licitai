"""
Testes de regressão do estruturador de documentos.

Cobrem os dois bugs corrigidos em documentos padrão SEI:
1. Número de seção/item em linha isolada ("1." seguido de "O OBJETO" na linha seguinte)
2. Dados de tabela (ex.: "9.000 BTU") que eram erroneamente detectados como itens
"""

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
