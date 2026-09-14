"""
Mapeamento de posições de linha para números de página.
"""


def _build_page_map(pages: list[dict]) -> list[tuple[int, int]]:
    """
    Constrói mapa de posição de linha → número de página.

    Alinha com `full_text = "\\n\\n".join(...)` em pdf_parser: páginas vazias
    são omitidas e cada junção entre páginas adiciona uma linha em branco extra.
    Returns: Lista de (posição_inicial, página)
    """
    page_map: list[tuple[int, int]] = []
    position = 0
    first = True
    for page_info in pages:
        text = page_info.get("text", "")
        if not text.strip():
            continue
        if not first:
            # Compensa o "\\n\\n" inserido entre páginas no join
            position += 1
        line_count = text.count("\n") + 1
        page_map.append((position, page_info["page"]))
        position += line_count
        first = False
    return page_map


def _get_page_for_position(line_idx: int, page_map: list[tuple[int, int]]) -> int:
    """Retorna o número da página para uma posição de linha."""
    page = 1
    for start_pos, page_num in page_map:
        if line_idx >= start_pos:
            page = page_num
        else:
            break
    return page
