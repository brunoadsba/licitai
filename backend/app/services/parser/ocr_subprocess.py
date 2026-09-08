"""OCR em subprocesso isolado com hard timeout."""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError
from multiprocessing import get_context
from pathlib import Path

logger = logging.getLogger(__name__)

OCR_HARD_TIMEOUT_SECONDS = 120


def _ocr_pages_sync(file_path: str, max_pages: int, max_ocr_pages: int) -> list[dict]:
    """Worker top-level (picklable) — executa OCR sem compartilhar o processo pai."""
    import io

    import fitz
    import pytesseract
    from PIL import Image

    pages: list[dict] = []
    doc = fitz.open(file_path)
    try:
        if doc.page_count > max_pages:
            raise ValueError(f"PDF excede o limite de {max_pages} páginas.")
        if doc.page_count > max_ocr_pages:
            raise ValueError(
                f"PDF escaneado excede cota OCR de {max_ocr_pages} páginas."
            )
        for page_num in range(doc.page_count):
            page = doc[page_num]
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(image, lang="por")
            pages.append({"page": page_num + 1, "text": text.strip()})
    finally:
        doc.close()
    return pages


def run_ocr_isolated(
    file_path: Path,
    *,
    max_pages: int,
    max_ocr_pages: int,
    timeout_seconds: float = OCR_HARD_TIMEOUT_SECONDS,
) -> list[dict]:
    """
    Executa OCR em processo separado e aplica hard timeout.

    Se o timeout estourar, o pool é encerrado (processo filho terminado).
    """
    ctx = get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=ctx) as pool:
        fut = pool.submit(
            _ocr_pages_sync, str(file_path), max_pages, max_ocr_pages
        )
        try:
            return fut.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            logger.error(
                "OCR hard-timeout após %.0fs para %s", timeout_seconds, file_path.name
            )
            # Cancelamento + shutdown do pool mata o worker.
            fut.cancel()
            raise ValueError(
                f"OCR excedeu o timeout hard de {int(timeout_seconds)}s."
            ) from exc
