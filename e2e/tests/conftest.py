import os
import time
from pathlib import Path

import httpx
import pytest


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_DOCX = FIXTURES_DIR / "sample-tr.docx"
# Análise multi-agente + rate limit free tier pode passar de 4 min
ANALYSIS_WAIT_ITERATIONS = int(os.getenv("E2E_ANALYSIS_WAIT_ITERS", "200"))
ANALYSIS_WAIT_SECONDS = float(os.getenv("E2E_ANALYSIS_WAIT_SECONDS", "2"))


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        yield client


@pytest.fixture(scope="module")
def sample_docx_path() -> Path:
    assert SAMPLE_DOCX.exists(), (
        f"Fixture não encontrada: {SAMPLE_DOCX}. "
        "Execute primeiro: python e2e/scripts/generate_fixture.py"
    )
    return SAMPLE_DOCX


def _upload_and_wait_parsed(api_client, sample_docx_path) -> dict:
    with open(sample_docx_path, "rb") as f:
        response = api_client.post(
            "/api/v1/documents/upload",
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
            pytest.fail(f"Parsing falhou: {body}")
        time.sleep(1)
    pytest.fail(f"Timeout aguardando parsing do documento {doc_id}")


@pytest.fixture
def uploaded_document(api_client, sample_docx_path):
    """Documento por teste (CRUD pode deletar sem afetar a análise)."""
    doc = _upload_and_wait_parsed(api_client, sample_docx_path)
    yield doc
    api_client.delete(f"/api/v1/documents/{doc['id']}")


@pytest.fixture(scope="module")
def analyzed_document(api_client, sample_docx_path):
    """Uma única análise LLM reutilizada pelos testes de Analysis/Report."""
    doc = _upload_and_wait_parsed(api_client, sample_docx_path)
    doc_id = doc["id"]

    response = api_client.post(f"/api/v1/analysis/{doc_id}/start")
    assert response.status_code == 202, f"Início da análise falhou: {response.text}"
    analysis_id = response.json()["analysis_id"]

    done = {"completed", "completed_with_errors"}
    for _ in range(ANALYSIS_WAIT_ITERATIONS):
        resp = api_client.get(f"/api/v1/analysis/{analysis_id}")
        assert resp.status_code == 200
        status = resp.json()["status"]
        if status in done:
            result = {
                "document": doc,
                "analysis": resp.json(),
                "analysis_id": analysis_id,
            }
            yield result
            api_client.delete(f"/api/v1/documents/{doc_id}")
            return
        if status == "error":
            api_client.delete(f"/api/v1/documents/{doc_id}")
            pytest.fail(f"Análise falhou: {resp.json()}")
        time.sleep(ANALYSIS_WAIT_SECONDS)

    api_client.delete(f"/api/v1/documents/{doc_id}")
    pytest.fail(
        f"Timeout aguardando análise {analysis_id} "
        f"({ANALYSIS_WAIT_ITERATIONS * ANALYSIS_WAIT_SECONDS:.0f}s)"
    )
