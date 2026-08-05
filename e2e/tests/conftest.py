import os
import uuid
from pathlib import Path

import httpx
import pytest


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_DOCX = FIXTURES_DIR / "sample-tr.docx"


@pytest.fixture
def api_client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        yield client


@pytest.fixture
def sample_docx_path() -> Path:
    assert SAMPLE_DOCX.exists(), (
        f"Fixture não encontrada: {SAMPLE_DOCX}. "
        "Execute primeiro: python e2e/scripts/generate_fixture.py"
    )
    return SAMPLE_DOCX


@pytest.fixture
def uploaded_document(api_client, sample_docx_path):
    with open(sample_docx_path, "rb") as f:
        response = api_client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample-tr.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert response.status_code == 201, f"Upload falhou: {response.text}"
    doc = response.json()
    yield doc
    api_client.delete(f"/api/v1/documents/{doc['id']}")


@pytest.fixture
def analyzed_document(api_client, uploaded_document):
    doc_id = uploaded_document["id"]
    response = api_client.post(f"/api/v1/analysis/{doc_id}/start")
    assert response.status_code == 202, f"Início da análise falhou: {response.text}"
    analysis_id = response.json()["analysis_id"]

    import time
    for _ in range(120):
        resp = api_client.get(f"/api/v1/analysis/{analysis_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status == "completed":
            return {"document": uploaded_document, "analysis": resp.json(), "analysis_id": analysis_id}
        if status == "error":
            pytest.fail(f"Análise falhou: {resp.json()}")
        time.sleep(2)

    pytest.fail("Timeout aguardando análise concluir")
