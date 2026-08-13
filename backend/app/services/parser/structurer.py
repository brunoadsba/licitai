"""
Estruturador de documentos.

Recebe texto bruto e identifica a estrutura hierárquica do documento:
- Seções numeradas (1., 1.1., 1.1.1.)
- Itens com letras (a), b), c))
- Alíneas romanas (I, II, III)
- Títulos
- Tabelas
- Anexos
"""

import logging

from app.services.parser.detection import PATTERNS, _detect_item_type, _is_footer_like
from app.services.parser.pagemap import _build_page_map, _get_page_for_position

logger = logging.getLogger(__name__)


def structure_items(raw_text: str, pages: list[dict]) -> list[dict]:
    """
    Estrutura o texto bruto em itens hierárquicos.

    Returns:
        Lista de dicts:
        {
            "item_number": "4.3.8",
            "title": "Horas Técnicas",
            "content": "texto completo do item...",
            "page_number": 18,
            "item_type": "item"  # section, item, subitem, table, annex
        }
    """
    # Construir mapa de página por posição no texto
    page_map = _build_page_map(pages)

    items = []
    lines = raw_text.split("\n")

    current_item = None
    current_content_lines = []
    in_table = False
    table_content = []

    line_idx = 0
    while line_idx < len(lines):
        stripped = lines[line_idx].strip()
        if not stripped:
            if current_content_lines:
                current_content_lines.append("")
            line_idx += 1
            continue

        # Verificar se estamos dentro de uma tabela
        if PATTERNS["table_start"].match(stripped):
            in_table = True
            table_content = []
            line_idx += 1
            continue
        if PATTERNS["table_end"].match(stripped):
            in_table = False
            if table_content:
                # Salvar tabela como item
                _save_current_item(items, current_item, current_content_lines)
                items.append({
                    "item_number": f"TAB-{len(items) + 1}",
                    "title": "Tabela",
                    "content": "\n".join(table_content),
                    "page_number": _get_page_for_position(line_idx, page_map),
                    "item_type": "table",
                })
                current_item = None
                current_content_lines = []
            line_idx += 1
            continue

        if in_table:
            table_content.append(stripped)
            line_idx += 1
            continue

        # Número em linha isolada (padrão SEI): "1." + "O OBJETO" em linhas separadas
        combined = _combine_isolated_number(lines, line_idx)
        if combined is not None:
            # Combinar e pular a linha do título já consumida
            stripped, line_idx = combined

        # Tentar identificar tipo de item
        detected = _detect_item_type(stripped)

        if detected:
            # Salvar item anterior
            _save_current_item(items, current_item, current_content_lines)

            # Iniciar novo item
            current_item = {
                "item_number": detected["number"],
                "title": detected["title"],
                "page_number": _get_page_for_position(line_idx, page_map),
                "item_type": detected["type"],
            }
            current_content_lines = [stripped]
        else:
            # Continuar acumulando conteúdo no item atual
            current_content_lines.append(stripped)

        line_idx += 1

    # Salvar último item
    _save_current_item(items, current_item, current_content_lines)

    # Se nenhum item foi detectado, criar um item único com todo o texto
    if not items:
        items.append({
            "item_number": "1",
            "title": "Documento Completo",
            "content": raw_text.strip(),
            "page_number": 1,
            "item_type": "section",
        })

    # Validar itens duplicados e conteúdo vazio
    seen_numbers: set[str] = set()
    validated = []
    for item in items:
        num = item.get("item_number", "")
        if not num or not item.get("content", "").strip():
            logger.warning("Item ignorado: número ou conteúdo vazio (%s)", num)
            continue
        if num in seen_numbers:
            suffix = 1
            while f"{num}-{suffix}" in seen_numbers:
                suffix += 1
            item["item_number"] = f"{num}-{suffix}"
            logger.warning("Item duplicado renomeado: %s -> %s", num, item["item_number"])
        seen_numbers.add(item["item_number"])
        validated.append(item)

    logger.info("Documento estruturado: %d itens identificados", len(validated))
    return validated


def _combine_isolated_number(lines: list[str], line_idx: int) -> tuple[str, int] | None:
    """
    Combina número em linha isolada com o título da linha seguinte (padrão SEI).

    Ex.: linha "1." seguida de "O OBJETO" vira "1. O OBJETO".

    Returns:
        Tuple (linha_combinada, índice_da_linha_combinada) ou None se não aplicar.
    """
    current = lines[line_idx].strip()
    if not PATTERNS["number_alone"].match(current):
        return None

    # Procurar a próxima linha não vazia
    next_idx = line_idx + 1
    while next_idx < len(lines) and not lines[next_idx].strip():
        next_idx += 1

    # Linha seguinte também é um número isolado → não combinar
    if next_idx >= len(lines) or PATTERNS["number_alone"].match(lines[next_idx].strip()):
        return None

    # Linha seguinte parece rodapé/cabeçalho de documento SEI → não combinar
    if _is_footer_like(lines[next_idx].strip()):
        return None

    return f"{current} {lines[next_idx].strip()}", next_idx


def _save_current_item(
    items: list[dict],
    current_item: dict | None,
    content_lines: list[str],
) -> None:
    """Salva o item atual na lista de itens."""
    if current_item and content_lines:
        content = "\n".join(content_lines).strip()
        if content:
            current_item["content"] = content
            items.append(current_item)
    content_lines.clear()
