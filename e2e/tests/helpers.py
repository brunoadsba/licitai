"""Helpers compartilhados pelos testes E2E HTTP."""

from __future__ import annotations

import os
import time
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_DOCX = FIXTURES_DIR / "sample-tr.docx"
BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
ANALYSIS_WAIT_ITERATIONS = int(os.getenv("E2E_ANALYSIS_WAIT_ITERS", "200"))
ANALYSIS_WAIT_SECONDS = float(os.getenv("E2E_ANALYSIS_WAIT_SECONDS", "2"))


def api_headers() -> dict[str, str]:
    token = os.getenv("E2E_API_TOKEN") or os.getenv("API_TOKEN") or ""
    if not token:
        return {}
    return {"X-API-Token": token}


def upload_and_wait_parsed(
    api_client,
    sample_docx_path,
    *,
    document_type: str = "tr",
    fornecedor_id: str | None = None,
) -> dict:
    data = {"document_type": document_type}
    if fornecedor_id:
        data["fornecedor_id"] = fornecedor_id
    with open(sample_docx_path, "rb") as f:
        response = api_client.post(
            "/api/v1/documents/upload",
            data=data,
            files={
                "file": (
                    "sample-tr.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert response.status_code == 201, f"Upload falhou: {response.text}"
    doc = response.json()
    doc_id = doc["id"]

    for _ in range(60):
        detail = api_client.get(f"/api/v1/documents/{doc_id}")
        assert detail.status_code == 200
        body = detail.json()
        status = body["status"]
        if status in ("parsed", "completed"):
            return body
        if status == "error":
            raise AssertionError(f"Parsing falhou: {body}")
        time.sleep(1)
    raise AssertionError(f"Timeout aguardando parsing do documento {doc_id}")
