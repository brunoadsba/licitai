"""Testes do OCR isolado (timeout hard que mata o processo)."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.parser.ocr_subprocess import run_ocr_isolated


def test_run_ocr_isolated_timeout_kills_process():
    fut = MagicMock()
    fut.result.side_effect = FuturesTimeoutError()
    pool = MagicMock()
    pool.submit.return_value = fut
    pool._processes = {}

    with patch(
        "app.services.parser.ocr_subprocess.ProcessPoolExecutor",
        return_value=pool,
    ), patch(
        "app.services.parser.ocr_subprocess._terminate_pool"
    ) as terminate:
        with pytest.raises(ValueError, match="timeout hard"):
            run_ocr_isolated(
                Path("/tmp/fake.pdf"),
                max_pages=10,
                max_ocr_pages=5,
                timeout_seconds=1,
            )
    terminate.assert_called_once_with(pool)
    pool.shutdown.assert_called_with(wait=False, cancel_futures=True)


def test_run_ocr_isolated_success():
    fut = MagicMock()
    fut.result.return_value = [{"page": 1, "text": "ola"}]
    pool = MagicMock()
    pool.submit.return_value = fut

    with patch(
        "app.services.parser.ocr_subprocess.ProcessPoolExecutor",
        return_value=pool,
    ):
        pages = run_ocr_isolated(
            Path("/tmp/fake.pdf"),
            max_pages=10,
            max_ocr_pages=5,
            timeout_seconds=30,
        )
    assert pages == [{"page": 1, "text": "ola"}]
    pool.submit.assert_called_once()
    pool.shutdown.assert_called_with(wait=False, cancel_futures=True)


def test_ocr_pages_sync_rejects_over_quota():
    from app.services.parser.ocr_subprocess import _ocr_pages_sync

    fake_doc = MagicMock()
    fake_doc.page_count = 99
    fake_doc.close = MagicMock()

    with patch("fitz.open", return_value=fake_doc):
        with pytest.raises(ValueError, match="cota OCR"):
            _ocr_pages_sync("/tmp/x.pdf", max_pages=500, max_ocr_pages=50)
    fake_doc.close.assert_called()
