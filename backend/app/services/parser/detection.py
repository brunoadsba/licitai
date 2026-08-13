"""
Heurísticas de detecção de itens em Termos de Referência.

Padrões de numeração e reconhecimento de tipos (seção, item, subitem,
alínea, anexo, cláusula) usados pelo estruturador.
"""

import hashlib
import re
import unicodedata

# Unidades de medida que indicam dados de tabela (não são títulos de itens)
UNIDADES_MEDIDA = {
    "btu", "kw", "kg", "m", "m²", "m³", "cm", "mm", "un", "unid", "und",
    "dia", "dias", "h", "hr", "hora", "horas", "l", "ml", "r$", "pct", "%",
    "ton", "t", "m³/h", "l/min", "v", "w",
}

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
