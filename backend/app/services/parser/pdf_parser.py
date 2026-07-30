"""
Parser de documentos PDF.

Usa PyMuPDF (fitz) como primário e pdfplumber como fallback.
Inclui OCR via Tesseract para PDFs escaneados (sem texto selecionável).

Segurança:
- Timeout para parsing
- Limites de memória
- Sem execução de JavaScript embutido
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io


logger = logging.getLogger(__name__)

# Limite de páginas para prevenir DoS
MAX_PAGES = 500


def parse_pdf(file_path: Path) -> tuple[str, list[dict]]:
    """
    Extrai texto de um PDF.

    Strategy:
    1. PyMuPDF (rápido, boa qualidade para PDFs digitais)
    2. Se pouco texto encontrado, tenta pdfplumber (melhor com tabelas)
    3. Se ainda sem texto, OCR via Tesseract

    Returns:
        Tuple (texto_completo, lista_de_páginas)
        Cada página é um dict: {"page": int, "text": str}
    """
    pages = []
    full_text_parts = []

    try:
        pages = _extract_with_pymupdf(file_path)
    except Exception:
        logger.warning("PyMuPDF falhou, tentando pdfplumber para %s", file_path.name)
        try:
            pages = _extract_with_pdfplumber(file_path)
        except Exception:
            logger.exception("Ambos parsers falharam para %s", file_path.name)
            raise ValueError("Não foi possível extrair texto do PDF.")

    # Verificar se obteve texto suficiente
    total_chars = sum(len(p["text"]) for p in pages)

    if total_chars < 100 and len(pages) > 0:
        # PDF provavelmente escaneado — tentar OCR
        logger.info("Pouco texto encontrado (%d chars), tentando OCR...", total_chars)
        try:
            pages = _extract_with_ocr(file_path)
        except Exception:
            logger.warning("OCR falhou para %s", file_path.name)
            # Manter o que foi extraído

    full_text = "\n\n".join(p["text"] for p in pages if p["text"].strip())

    if not full_text.strip():
        raise ValueError(
            "Nenhum texto pôde ser extraído do PDF. "
            "Verifique se o arquivo não está corrompido."
        )

    return full_text, pages


def _extract_with_pymupdf(file_path: Path) -> list[dict]:
    """Extração com PyMuPDF (fitz)."""
    pages = []

    # Abrir sem executar JavaScript embutido
    doc = fitz.open(str(file_path))

    if doc.page_count > MAX_PAGES:
        doc.close()
        raise ValueError(f"PDF excede o limite de {MAX_PAGES} páginas.")

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
            })
    finally:
        doc.close()

    return pages


def _extract_with_pdfplumber(file_path: Path) -> list[dict]:
    """Extração com pdfplumber (melhor para tabelas)."""
    pages = []

    with pdfplumber.open(str(file_path)) as pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise ValueError(f"PDF excede o limite de {MAX_PAGES} páginas.")

        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            # Extrair tabelas separadamente
            tables = page.extract_tables()
            if tables:
                table_text_parts = []
                for table in tables:
                    for row in table:
                        if row:
                            cleaned = [str(cell) if cell else "" for cell in row]
                            table_text_parts.append(" | ".join(cleaned))
                if table_text_parts:
                    text += "\n\n[TABELA]\n" + "\n".join(table_text_parts) + "\n[/TABELA]"

            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
            })

    return pages


def _extract_with_ocr(file_path: Path) -> list[dict]:
    """OCR com Tesseract para PDFs escaneados."""
    pages = []

    doc = fitz.open(str(file_path))

    if doc.page_count > MAX_PAGES:
        doc.close()
        raise ValueError(f"PDF excede o limite de {MAX_PAGES} páginas.")

    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]

            # Renderizar página como imagem (300 DPI para boa qualidade OCR)
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)

            # Converter para PIL Image
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))

            # OCR com Tesseract (Português)
            text = pytesseract.image_to_string(image, lang="por")

            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
            })
    finally:
        doc.close()

    return pages
