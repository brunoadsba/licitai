"""Detecção de sumário/rodapé/início do corpo — extraído de `detection.py`."""

import re

from app.services.parser.detection_items import _detect_item_type
from app.services.parser.detection_patterns import (
    _MIN_BODY_CHARS,
    _MIN_BODY_WORDS,
    _SENTENCE_PUNCT,
    PATTERNS,
)


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


def _is_toc_start(line: str) -> bool:
    """Linha que inicia bloco de sumário/índice."""
    return bool(PATTERNS["toc_start"].match(line.strip()))


def _is_toc_end(line: str) -> bool:
    """
    Linha que encerra o bloco de sumário (início do corpo do TR).

    Ignora rodapés SEI do tipo
    "Termo de Referência / Projeto Básico 3 versão 2.0 … SEI …".
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Rodapé / cabeçalho de página — não encerra o sumário
    lowered = stripped.lower()
    if "sei " in lowered or "sei nº" in lowered or " / pg." in lowered:
        return False
    if "versão" in lowered and any(ch.isdigit() for ch in stripped):
        # "Termo de Referência / Projeto Básico 3 versão 2.0 (...)"
        if len(stripped) > 40:
            return False
    return bool(PATTERNS["toc_end"].match(stripped))


# Reinício tipicamente do corpo: seção 1 / 01 / cláusula / número isolado "1."
_BODY_RESTART = re.compile(
    r"^(?:"
    r"0?1\s*[.\-–]\s+.+"  # 1. Objeto / 01 – OBJETO
    r"|0?1\.$"  # número isolado SEI "1."
    r"|CL[AÁ]USULA\s+\w+"
    r")",
    re.IGNORECASE,
)


def _is_section_one_number(number: str) -> bool:
    """True se o número pertence à seção/item 1 / 1.x / 01."""
    n = (number or "").strip().lower()
    if not n:
        return False
    if n in {"1", "01"}:
        return True
    return bool(re.match(r"^0?1\.", n))


def _looks_like_body_start(lines: list[str], line_idx: int) -> bool:
    """
    Detecta saída do sumário quando o corpo começa sem cabeçalho TERMO DE REFERÊNCIA.

    Critério: linha parece reinício da seção 1/cláusula E há parágrafo substantivo
    *imediatamente sob este cabeçalho* (não linhas distantes do corpo).
    """
    stripped = lines[line_idx].strip()
    if not stripped or not _BODY_RESTART.match(stripped):
        return False
    if _is_footer_like(stripped):
        return False

    content_parts: list[str] = []
    i = line_idx + 1
    scanned = 0
    while i < len(lines) and scanned < 12:
        s = lines[i].strip()
        i += 1
        if not s:
            continue
        scanned += 1
        if _is_footer_like(s):
            continue
        if PATTERNS["number_alone"].match(s):
            # "1.1." isolado — ainda na hierarquia; próximo título/corpo vem depois
            continue
        detected = _detect_item_type(s)
        if detected:
            num = str(detected.get("number") or "")
            # Subitens 1.x: ainda no objeto; seção 2+: fim do bloco
            if _is_section_one_number(num):
                continue
            break
        content_parts.append(s)
        if len(content_parts) >= 5:
            break

    if not content_parts:
        return False

    compact = re.sub(r"\s+", " ", " ".join(content_parts)).strip()
    if len(compact) < _MIN_BODY_CHARS:
        return False
    words = [w for w in re.split(r"\s+", compact) if w]
    if len(words) < _MIN_BODY_WORDS:
        return False
    if not any(ch in _SENTENCE_PUNCT for ch in compact):
        return False
    return True
