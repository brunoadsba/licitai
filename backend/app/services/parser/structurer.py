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
import re

logger = logging.getLogger(__name__)

# Padrões de numeração comuns em TRs
PATTERNS = {
    # 1. ou 1 - (seção principal)
    "section": re.compile(r"^(\d{1,2})\s*[.\-–]\s+(.+)", re.MULTILINE),

    # 1.1 ou 1.1. (item)
    "item": re.compile(r"^(\d{1,2}\.\d{1,3})\s*\.?\s+(.+)", re.MULTILINE),

    # 1.1.1 ou 1.1.1. (subitem)
    "subitem": re.compile(r"^(\d{1,2}\.\d{1,3}\.\d{1,3})\s*\.?\s+(.+)", re.MULTILINE),

    # 1.1.1.1 (sub-subitem)
    "subsubitem": re.compile(r"^(\d{1,2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\.?\s+(.+)", re.MULTILINE),

    # a) ou a. (alínea)
    "letter": re.compile(r"^([a-z])\s*[).]\s+(.+)", re.MULTILINE),

    # I, II, III (romano)
    "roman": re.compile(r"^((?:X{0,3}(?:IX|IV|V?I{0,3})))\s*[).\-]\s+(.+)", re.MULTILINE | re.IGNORECASE),

    # [TÍTULO] marcado pelo parser
    "title_marker": re.compile(r"^\[TÍTULO\]\s+(.+)", re.MULTILINE),

    # CLÁUSULA ou DO/DA/DOS/DAS (padrão SEI)
    "clause": re.compile(r"^(CLÁUSULA\s+\w+|D[OA]S?\s+.+)", re.MULTILINE),

    # ANEXO
    "annex": re.compile(r"^(ANEXO\s+[IVXLCDM\d]+)\s*[.\-–]?\s*(.*)", re.MULTILINE | re.IGNORECASE),

    # Tabela marcada
    "table_start": re.compile(r"^\[TABELA\]", re.MULTILINE),
    "table_end": re.compile(r"^\[/TABELA\]", re.MULTILINE),
}


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

    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if current_content_lines:
                current_content_lines.append("")
            continue

        # Verificar se estamos dentro de uma tabela
        if PATTERNS["table_start"].match(stripped):
            in_table = True
            table_content = []
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
            continue

        if in_table:
            table_content.append(stripped)
            continue

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

    logger.info("Documento estruturado: %d itens identificados", len(items))
    return items


def _detect_item_type(line: str) -> dict | None:
    """Detecta o tipo de item a partir de uma linha."""

    # Ordem de prioridade: mais específico primeiro

    # Anexo
    m = PATTERNS["annex"].match(line)
    if m:
        return {
            "number": m.group(1).strip(),
            "title": m.group(2).strip() if m.group(2) else "",
            "type": "annex",
        }

    # Cláusula SEI
    m = PATTERNS["clause"].match(line)
    if m:
        return {
            "number": m.group(1).strip()[:50],
            "title": m.group(1).strip(),
            "type": "section",
        }

    # Título marcado pelo parser
    m = PATTERNS["title_marker"].match(line)
    if m:
        return {
            "number": f"T-{hash(m.group(1)) % 1000}",
            "title": m.group(1).strip(),
            "type": "section",
        }

    # Sub-subitem (1.1.1.1)
    m = PATTERNS["subsubitem"].match(line)
    if m:
        return {
            "number": m.group(1).strip(),
            "title": m.group(2).strip()[:200],
            "type": "subitem",
        }

    # Subitem (1.1.1)
    m = PATTERNS["subitem"].match(line)
    if m:
        return {
            "number": m.group(1).strip(),
            "title": m.group(2).strip()[:200],
            "type": "subitem",
        }

    # Item (1.1)
    m = PATTERNS["item"].match(line)
    if m:
        return {
            "number": m.group(1).strip(),
            "title": m.group(2).strip()[:200],
            "type": "item",
        }

    # Seção (1.)
    m = PATTERNS["section"].match(line)
    if m:
        return {
            "number": m.group(1).strip(),
            "title": m.group(2).strip()[:200],
            "type": "section",
        }

    return None


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
