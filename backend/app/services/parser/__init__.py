"""
Pacote de parsing de documentos.

Os parsers concretos são síncronos e CPU-bound (PyMuPDF/pdfplumber/Tesseract);
aqui eles são offloadados para uma thread via asyncio.to_thread para não
bloquear o event loop durante uploads (OCR pode levar minutos).

Hard timeout do parse: asyncio.wait_for em torno do to_thread.
OCR usa subprocesso isolado com SIGKILL se estourar o timeout.
"""

import asyncio
import logging
import os

from app.services.ingest.hashing import sha256_text
from app.services.parser.docx_parser import parse_docx
from app.services.parser.legal_marks import extract_legal_marks
from app.services.parser.odt_parser import parse_odt
from app.services.parser.pdf_parser import parse_pdf
from app.services.parser.schema import ParseItem, ParsePage, ParseResult
from app.services.parser.structurer import structure_items

logger = logging.getLogger(__name__)

__all__ = [
    "parse_pdf",
    "parse_docx",
    "parse_odt",
    "structure_items",
    "parse_document",
    "ParseResult",
]

# Timeout global de parsing (inclui OCR). Ajuste via env futuro se necessário.
PARSE_TIMEOUT_SECONDS = float(os.getenv("PARSE_TIMEOUT_SECONDS", "180"))
_PARSE_SEMAPHORE = asyncio.Semaphore(max(1, int(os.getenv("PARSE_MAX_CONCURRENT", "2"))))


async def parse_document(file_path, file_type: str) -> ParseResult:
    """Parseia em thread e devolve estrutura intermediária validável."""
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
        async with _PARSE_SEMAPHORE:
            raw_text, pages = await asyncio.wait_for(coro, timeout=PARSE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        logger.error(
            "parse.timeout file=%s type=%s limit=%.0fs orphan_thread=possible",
            file_path.name, file_type, PARSE_TIMEOUT_SECONDS,
        )
        raise TimeoutError(
            f"Parsing excedeu {PARSE_TIMEOUT_SECONDS:.0f}s (possível OCR pesado)."
        ) from exc

    items = structure_items(raw_text, pages)
    return ParseResult(
        content_hash=sha256_text(raw_text),
        extractor=file_type,
        pages=[ParsePage.model_validate(page) for page in pages],
        items=[ParseItem.model_validate(item) for item in items],
        marks=extract_legal_marks(raw_text),
        raw_text=raw_text,
    )
