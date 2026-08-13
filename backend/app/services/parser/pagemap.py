"""
Mapeamento de posições de linha para números de página.
"""


def _build_page_map(pages: list[dict]) -> list[tuple[int, int]]:
    """
    Constrói mapa de posição de linha → número de página.
    Returns: Lista de (posição_inicial, página)
    """
    page_map = []
    position = 0
    for page_info in pages:
        text = page_info.get("text", "")
        line_count = text.count("\n") + 1
        page_map.append((position, page_info["page"]))
        position += line_count
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
