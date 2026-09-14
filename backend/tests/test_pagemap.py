"""Testes do mapeamento linha → página (alinhado ao join \\n\\n do PDF)."""

from app.services.parser.pagemap import _build_page_map, _get_page_for_position


def test_page_map_compensa_join_entre_paginas():
    pages = [
        {"page": 1, "text": "linhaA"},
        {"page": 2, "text": "linhaB"},
        {"page": 3, "text": "linhaC"},
    ]
    page_map = _build_page_map(pages)
    # full_text = "linhaA\\n\\nlinhaB\\n\\nlinhaC" → índices 0, 2, 4
    assert page_map == [(0, 1), (2, 2), (4, 3)]
    assert _get_page_for_position(0, page_map) == 1
    assert _get_page_for_position(2, page_map) == 2
    assert _get_page_for_position(4, page_map) == 3


def test_page_map_ignora_paginas_vazias():
    pages = [
        {"page": 1, "text": "a"},
        {"page": 2, "text": "   "},
        {"page": 3, "text": "b"},
    ]
    page_map = _build_page_map(pages)
    assert page_map == [(0, 1), (2, 3)]
