"""Parser DOCX: ordem do corpo, tachado, títulos e notas."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)


def parse_docx(file_path: Path) -> tuple[str, list[dict]]:
    """Extrai texto de um DOCX preservando a ordem de parágrafos e tabelas."""
    try:
        doc = DocxDocument(str(file_path))
    except Exception as exc:
        logger.exception("Erro ao abrir DOCX: %s", file_path.name)
        raise ValueError(
            "Não foi possível abrir o arquivo DOCX. Verifique o formato."
        ) from exc

    text_parts: list[str] = []
    for block in _iter_body_blocks(doc):
        if isinstance(block, Paragraph):
            piece = _format_paragraph(block)
            if piece:
                text_parts.append(piece)
        elif isinstance(block, Table):
            text_parts.extend(_format_table(block))

    full_text = "\n".join(text_parts)
    if not full_text.strip():
        raise ValueError(
            "Nenhum texto pôde ser extraído do DOCX. "
            "Verifique se o arquivo não está vazio ou corrompido."
        )
    return full_text, [{"page": 1, "text": full_text}]


def _iter_body_blocks(doc: DocxDocument):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _is_strike(run) -> bool:
    if getattr(run.font, "strike", None):
        return True
    rpr = run._element.find(qn("w:rPr"))
    if rpr is None:
        return False
    return (
        rpr.find(qn("w:strike")) is not None
        or rpr.find(qn("w:dstrike")) is not None
    )


def _paragraph_text(para: Paragraph) -> str:
    if not para.runs:
        return (para.text or "").strip()
    parts: list[str] = []
    for run in para.runs:
        text = run.text or ""
        if not text:
            continue
        if _is_strike(run):
            parts.append(f"[TACHADO]{text}[/TACHADO]")
        else:
            parts.append(text)
    return "".join(parts).strip()


def _format_paragraph(para: Paragraph) -> str:
    text = _paragraph_text(para)
    if not text:
        return ""
    style = para.style.name if para.style else ""
    if any(key in style for key in ("Heading", "Título")):
        return f"[TÍTULO] {text}"
    if any(key in style for key in ("Footnote", "Endnote", "Nota")):
        return f"[NOTA] {text}"
    if any(key in style for key in ("List", "Lista")):
        return f"  • {text}"
    return text


def _format_table(table: Table) -> list[str]:
    rows: list[str] = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    if not rows:
        return []
    return ["[TABELA]", *rows, "[/TABELA]"]
