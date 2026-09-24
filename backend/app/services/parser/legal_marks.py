"""Normaliza marcações jurídicas: tachado, (VETADO) e redação dada."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.parser.schema import LegalMark

STRIKE_RE = re.compile(
    r"~~(.+?)~~|\[TACHADO\](.+?)\[/TACHADO\]",
    re.DOTALL,
)
REDACAO_RE = re.compile(
    r"\(\s*Redação\s+dada\s+pela\s+([^)]+)\)",
    re.IGNORECASE,
)
VETADO_INLINE_RE = re.compile(r"\(\s*VETADO\s*\)", re.IGNORECASE)
VETADO_LINE_RE = re.compile(r"^\s*\(\s*VETADO\s*\)\s*$", re.IGNORECASE)
ARTICLE_HEADER_RE = re.compile(
    r"^(?:Art\.|Artigo)\s*\d+[º°\-A-Z]?",
    re.IGNORECASE,
)


@dataclass
class NormalizedLegalText:
    vigente: str
    marks: list[LegalMark] = field(default_factory=list)


def extract_legal_marks(content: str) -> list[LegalMark]:
    return normalize_legal_text(content).marks


def normalize_legal_text(content: str) -> NormalizedLegalText:
    """Separa redação histórica da vigente sem misturar os dois no índice."""
    marks: list[LegalMark] = []

    def _strike(match: re.Match[str]) -> str:
        inner = (match.group(1) or match.group(2) or "").strip()
        if inner:
            marks.append(
                LegalMark(kind="strikethrough", text=inner, status="historical")
            )
        return ""

    text = STRIKE_RE.sub(_strike, content)

    for match in REDACAO_RE.finditer(text):
        marks.append(
            LegalMark(
                kind="redacao_dada",
                text=match.group(0),
                status="annotation",
                citation=match.group(1).strip(),
            )
        )

    vigente_lines = _strip_vetado_blocks(text, marks)
    vigente = "\n".join(vigente_lines)
    vigente = re.sub(r"[ \t]+\n", "\n", vigente)
    vigente = re.sub(r"\n{3,}", "\n\n", vigente)
    return NormalizedLegalText(vigente=vigente.strip(), marks=marks)


def _only_vetado(rest: str) -> bool:
    cleaned = rest.strip(" .-–—")
    return bool(cleaned) and VETADO_INLINE_RE.fullmatch(cleaned) is not None


def _strip_vetado_blocks(text: str, marks: list[LegalMark]) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        header = ARTICLE_HEADER_RE.match(stripped)
        if header:
            rest = stripped[header.end() :].strip()
            nxt = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            if rest and _only_vetado(rest):
                marks.append(
                    LegalMark(kind="vetado", text=stripped, status="historical")
                )
                idx += 1
                continue
            if not rest and VETADO_LINE_RE.match(nxt):
                marks.append(
                    LegalMark(
                        kind="vetado",
                        text=f"{stripped} {nxt}",
                        status="historical",
                    )
                )
                idx += 2
                continue
            if rest and VETADO_INLINE_RE.search(rest) and not _only_vetado(rest):
                marks.append(
                    LegalMark(kind="vetado", text="(VETADO)", status="historical")
                )
                out.append(VETADO_INLINE_RE.sub("", line))
                idx += 1
                continue
        elif VETADO_INLINE_RE.search(stripped):
            marks.append(
                LegalMark(kind="vetado", text="(VETADO)", status="historical")
            )
            cleaned = VETADO_INLINE_RE.sub("", line)
            if cleaned.strip():
                out.append(cleaned)
            idx += 1
            continue
        out.append(line)
        idx += 1
    return out
