"""Detecção de tipos de item por linha — extraído de `detection.py`."""

import hashlib
import re
import unicodedata

from app.services.parser.detection_patterns import PATTERNS, UNIDADES_MEDIDA


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
