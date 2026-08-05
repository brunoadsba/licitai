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

import hashlib
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Unidades de medida que indicam dados de tabela (não são títulos de itens)
UNIDADES_MEDIDA = {
    "btu", "kw", "kg", "m", "m²", "m³", "cm", "mm", "un", "unid", "und",
    "dia", "dias", "h", "hr", "hora", "horas", "l", "ml", "r$", "pct", "%",
    "ton", "t", "m³/h", "l/min", "v", "w",
}


def _is_table_data_title(title: str) -> bool:
    """Verifica se o título parece dado de tabela (unidade de medida ou valor)."""
    clean = title.strip().lower()
    if not clean:
        return True
    # Apenas unidade de medida (ex.: "BTU", "R$")
    if clean in UNIDADES_MEDIDA:
        return True
    # Unidade composta: "dias úteis", "R$ 1.234,56"
    if clean.startswith("dias úteis") or clean.startswith("r$"):
        return True
    return False

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

    # Número em linha isolada (padrão SEI): "1." seguido do título na linha seguinte
    "number_alone": re.compile(r"^\d{1,2}(\.\d{1,3})*\.$"),

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


def _is_footer_like(line: str) -> bool:
    """Detecta linhas de rodapé/cabeçalho típicas de documentos SEI."""
    footer_markers = (
        "referência: processo",
        "sei nº",
        "sei n.",
        "termo de referência / projeto básico",
        "telefone:",
        "www.",
        "pg.",
        "processo nº",
        "cep",
    )
    lowered = line.lower()
    return any(marker in lowered for marker in footer_markers)


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
        _raw_title = unicodedata.normalize("NFC", m.group(1).strip())
        _digest = hashlib.sha256(_raw_title.encode("utf-8")).hexdigest()
        _number = f"T-{int(_digest[:12], 16) % 100000}"
        return {
            "number": _number,
            "title": m.group(1).strip(),
            "type": "section",
        }

    m = PATTERNS["letter"].match(line)
    if m:
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip().lower(),
            "title": title[:200],
            "type": "subitem",
        }

    m = PATTERNS["roman"].match(line)
    if m:
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip().upper(),
            "title": title[:200],
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
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip(),
            "title": title[:200],
            "type": "item",
        }

    # Seção (1.)
    m = PATTERNS["section"].match(line)
    if m:
        title = m.group(2).strip()
        if _is_table_data_title(title):
            return None
        return {
            "number": m.group(1).strip(),
            "title": title[:200],
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
