"""OCR em subprocesso isolado com hard timeout que mata o processo."""

from __future__ import annotations

import logging
import os
import signal
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


def _terminate_pool(pool: ProcessPoolExecutor) -> None:
    """Encerra os processos do pool (SIGKILL). O timeout não pode só cancelar o Future."""
    processes = getattr(pool, "_processes", None) or {}
    for proc in list(processes.values()):
        pid = getattr(proc, "pid", None)
        if not pid:
            kill = getattr(proc, "kill", None)
            if callable(kill):
                kill()
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue


def run_ocr_isolated(
    file_path: Path,
    *,
    max_pages: int,
    max_ocr_pages: int,
    timeout_seconds: float = OCR_HARD_TIMEOUT_SECONDS,
) -> list[dict]:
    """
    Executa OCR em processo separado e aplica hard timeout.

    Se o timeout estourar, os processos filhos são mortos — o `with`
    ProcessPoolExecutor faria shutdown(wait=True) e esperaria o OCR acabar.
    """
    ctx = get_context("spawn")
    pool = ProcessPoolExecutor(max_workers=1, mp_context=ctx)
    try:
        fut = pool.submit(
            _ocr_pages_sync, str(file_path), max_pages, max_ocr_pages
        )
        try:
            return fut.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            logger.error(
                "OCR hard-timeout após %.0fs para %s",
                timeout_seconds,
                file_path.name,
            )
            _terminate_pool(pool)
            raise ValueError(
                f"OCR excedeu o timeout hard de {int(timeout_seconds)}s."
            ) from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
