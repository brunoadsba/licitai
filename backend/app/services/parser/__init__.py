"""
Pacote de parsing de documentos.

Os parsers concretos são síncronos e CPU-bound (PyMuPDF/pdfplumber/Tesseract);
aqui eles são offloadados para uma thread via asyncio.to_thread para não
bloquear o event loop durante uploads (OCR pode levar minutos).
"""

import asyncio

from app.services.parser.docx_parser import parse_docx
from app.services.parser.odt_parser import parse_odt
from app.services.parser.pdf_parser import parse_pdf
from app.services.parser.structurer import structure_items

__all__ = ["parse_pdf", "parse_docx", "parse_odt", "structure_items", "parse_document"]


async def parse_document(file_path, file_type: str) -> list[dict]:
    """Parseia documento em thread separada e retorna itens estruturados."""
    from pathlib import Path

    file_path = Path(file_path)

    if file_type == "pdf":
        raw_text, pages = await asyncio.to_thread(parse_pdf, file_path)
    elif file_type == "docx":
        raw_text, pages = await asyncio.to_thread(parse_docx, file_path)
    elif file_type == "odt":
        raw_text, pages = await asyncio.to_thread(parse_odt, file_path)
    else:
        raise ValueError(f"Tipo não suportado: {file_type}")

    return structure_items(raw_text, pages)
