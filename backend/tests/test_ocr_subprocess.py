"""Testes do OCR isolado (timeout hard)."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.parser.ocr_subprocess import run_ocr_isolated


def test_run_ocr_isolated_timeout_raises():
    fut = MagicMock()
    fut.result.side_effect = FuturesTimeoutError()
    pool = MagicMock()
    pool.__enter__.return_value = pool
    pool.__exit__.return_value = False
    pool.submit.return_value = fut

    with patch(
        "app.services.parser.ocr_subprocess.ProcessPoolExecutor",
        return_value=pool,
    ):
        with pytest.raises(ValueError, match="timeout hard"):
            run_ocr_isolated(
                Path("/tmp/fake.pdf"),
                max_pages=10,
                max_ocr_pages=5,
                timeout_seconds=1,
            )
    fut.cancel.assert_called()


def test_run_ocr_isolated_success():
    fut = MagicMock()
    fut.result.return_value = [{"page": 1, "text": "ola"}]
    pool = MagicMock()
    pool.__enter__.return_value = pool
    pool.__exit__.return_value = False
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


def test_ocr_pages_sync_rejects_over_quota():
    from app.services.parser.ocr_subprocess import _ocr_pages_sync

    fake_doc = MagicMock()
    fake_doc.page_count = 99
    fake_doc.close = MagicMock()

    with patch("fitz.open", return_value=fake_doc):
        with pytest.raises(ValueError, match="cota OCR"):
            _ocr_pages_sync("/tmp/x.pdf", max_pages=500, max_ocr_pages=50)
    fake_doc.close.assert_called()
