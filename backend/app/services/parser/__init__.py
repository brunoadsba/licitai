"""
Pacote de parsing de documentos.
"""

from app.services.parser.pdf_parser import parse_pdf
from app.services.parser.docx_parser import parse_docx
from app.services.parser.structurer import structure_items

__all__ = ["parse_pdf", "parse_docx", "structure_items", "parse_document"]


async def parse_document(file_path, file_type: str) -> list[dict]:
    """Parseia documento e retorna itens estruturados."""
    from pathlib import Path

    file_path = Path(file_path)

    if file_type == "pdf":
        raw_text, pages = parse_pdf(file_path)
    elif file_type == "docx":
        raw_text, pages = parse_docx(file_path)
    else:
        raise ValueError(f"Tipo não suportado: {file_type}")

    return structure_items(raw_text, pages)
