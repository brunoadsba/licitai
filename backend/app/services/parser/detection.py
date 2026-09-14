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

    # Sumário / Índice (início do bloco)
    "toc_start": re.compile(
        r"^(SUM[AÁ]RIO|ÍNDICE|INDICE)(\s|$)",
        re.IGNORECASE,
    ),

    # Fim típico do sumário: título do corpo do documento (linha curta, sem rodapé)
    "toc_end": re.compile(
        r"^(TERMO\s+DE\s+REFER[EÊ]NCIA(\s+(OU|/)\s+PROJETO\s+B[AÁ]SICO)?|"
        r"PROJETO\s+B[AÁ]SICO)\s*$",
        re.IGNORECASE,
    ),
}


# Mínimos para considerar conteúdo substantivo (cláusula real, não só título)
_MIN_BODY_CHARS = 50
_MIN_BODY_WORDS = 8
_SENTENCE_PUNCT = frozenset(".…;:")


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
