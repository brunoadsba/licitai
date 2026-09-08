"""
Pacote de parsing de documentos.

Os parsers concretos são síncronos e CPU-bound (PyMuPDF/pdfplumber/Tesseract);
aqui eles são offloadados para uma thread via asyncio.to_thread para não
bloquear o event loop durante uploads (OCR pode levar minutos).

Hard timeout: asyncio.wait_for em torno do to_thread. OCR em subprocesso
isolado com kill forçado fica fora do MVP (complexidade de IPC + Tesseract);
o timeout do to_thread cancela a await, mas a thread pode continuar até o
fim do OCR da página corrente — aceitável no piloto single-user.
"""

import asyncio
import logging

from app.services.parser.docx_parser import parse_docx
from app.services.parser.odt_parser import parse_odt
from app.services.parser.pdf_parser import parse_pdf
from app.services.parser.structurer import structure_items

logger = logging.getLogger(__name__)

__all__ = ["parse_pdf", "parse_docx", "parse_odt", "structure_items", "parse_document"]

# Timeout global de parsing (inclui OCR). Ajuste via env futuro se necessário.
PARSE_TIMEOUT_SECONDS = 180.0


async def parse_document(file_path, file_type: str) -> list[dict]:
    """Parseia documento em thread separada e retorna itens estruturados."""
    from pathlib import Path

    file_path = Path(file_path)

    if file_type == "pdf":
        coro = asyncio.to_thread(parse_pdf, file_path)
    elif file_type == "docx":
        coro = asyncio.to_thread(parse_docx, file_path)
    elif file_type == "odt":
        coro = asyncio.to_thread(parse_odt, file_path)
    else:
        raise ValueError(f"Tipo não suportado: {file_type}")

    try:
        raw_text, pages = await asyncio.wait_for(coro, timeout=PARSE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        logger.error(
            "parse.timeout file=%s type=%s limit=%.0fs",
            file_path.name, file_type, PARSE_TIMEOUT_SECONDS,
        )
        raise TimeoutError(
            f"Parsing excedeu {PARSE_TIMEOUT_SECONDS:.0f}s (possível OCR pesado)."
        ) from exc

    return structure_items(raw_text, pages)
