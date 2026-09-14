"""Testes do parse de leis / RILC (Art. e Artigo + marcador de página)."""

from app.services.rag.loader import parse_law_text


def test_parse_law_text_art_federal():
    content = (
        "Art. 1º Esta lei regula.\n"
        "Parágrafo único. Detalhe.\n"
        "Art. 2º Segundo artigo.\n"
    )
    chunks = parse_law_text(content)
    assert [c.article for c in chunks] == ["Art. 1º", "Art. 2º"]
    assert "Parágrafo único" in chunks[0].text


def test_parse_law_text_artigo_rilc_com_pagina():
    content = (
        "# Página 31\n"
        "Artigo 52. O termo de referência deve conter o objeto.\n"
        "I - definição clara;\n"
        "# Página 32\n"
        "Artigo 53. A estimativa de preços é obrigatória.\n"
    )
    chunks = parse_law_text(content)
    assert len(chunks) == 2
    assert chunks[0].article == "Art. 52"
    assert chunks[0].page == 31
    assert "definição clara" in chunks[0].text
    assert chunks[1].article == "Art. 53"
    assert chunks[1].page == 32
