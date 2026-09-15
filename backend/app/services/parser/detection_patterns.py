"""Padrões de numeração e constantes de detecção — extraído de `detection.py`."""

import re

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
