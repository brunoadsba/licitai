"""Conteúdo substantivo (cláusula vs título) — extraído de `detection.py`."""

import re

from app.services.parser.detection_patterns import (
    _MIN_BODY_CHARS,
    _MIN_BODY_WORDS,
    _SENTENCE_PUNCT,
)


def _strip_heading_prefix(
    content: str,
    title: str | None,
    item_number: str | None,
) -> str:
    """Remove número e título do início do conteúdo, deixando só o corpo."""
    body = (content or "").strip()
    if not body:
        return ""

    # Remover primeira linha se for só o cabeçalho
    lines = body.split("\n")
    first = lines[0].strip()
    candidates: list[str] = []
    if title:
        candidates.append(title.strip())
    if item_number and title:
        candidates.extend(
            [
                f"{item_number} {title}".strip(),
                f"{item_number}. {title}".strip(),
                f"{item_number} – {title}".strip(),
                f"{item_number} - {title}".strip(),
                f"{item_number}—{title}".strip(),
            ]
        )
    if item_number:
        candidates.append(item_number.strip())

    normalized_first = re.sub(r"\s+", " ", first).casefold()
    for cand in candidates:
        if not cand:
            continue
        if normalized_first == re.sub(r"\s+", " ", cand).casefold():
            return "\n".join(lines[1:]).strip()

    # Conteúdo inteiro idêntico ao título/cabeçalho
    normalized_body = re.sub(r"\s+", " ", body).casefold()
    for cand in candidates:
        if cand and normalized_body == re.sub(r"\s+", " ", cand).casefold():
            return ""

    return body


def is_substantive_content(
    content: str,
    title: str | None = None,
    item_number: str | None = None,
    item_type: str | None = None,
) -> bool:
    """
    Indica se o item tem texto de cláusula (obrigação, descrição, regra).

    Títulos, tópicos e subtópicos sem corpo retornam False — não devem
    ir para a LLM. Tabelas não são auditadas como cláusula.
    """
    if item_type == "table":
        return False

    body = _strip_heading_prefix(content, title, item_number)
    if not body:
        return False

    # Remover espaços e medir corpo restante
    compact = re.sub(r"\s+", " ", body).strip()
    if len(compact) < _MIN_BODY_CHARS:
        return False

    words = [w for w in re.split(r"\s+", compact) if w]
    if len(words) < _MIN_BODY_WORDS:
        return False

    if not any(ch in _SENTENCE_PUNCT for ch in compact):
        return False

    return True
