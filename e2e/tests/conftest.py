"""
Fixtures E2E HTTP + markers.

Markers:
  e2e_fast — sem LLM longo (CRUD, guards, listagens)
  e2e_live — precisa worker + LLM (ou análise já existente)
  e2e_full_flow — suite histórica test_e2e_full_flow.py
"""

from __future__ import annotations

import time

import httpx
import pytest

from helpers import (
    ANALYSIS_WAIT_ITERATIONS,
    ANALYSIS_WAIT_SECONDS,
    SAMPLE_DOCX,
    api_headers,
    upload_and_wait_parsed,
)


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e_fast: testes E2E sem LLM longo")
    config.addinivalue_line("markers", "e2e_live: testes E2E com LLM/worker")
    config.addinivalue_line("markers", "e2e_full_flow: suite histórica full_flow")


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(base_url=os_base(), timeout=60, headers=api_headers()) as client:
        yield client


def os_base() -> str:
    import os

    return os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="module")
def sample_docx_path():
    assert SAMPLE_DOCX.exists(), (
        f"Fixture não encontrada: {SAMPLE_DOCX}. "
        "Execute primeiro: python e2e/scripts/generate_fixture.py"
    )
    return SAMPLE_DOCX


@pytest.fixture
def uploaded_document(api_client, sample_docx_path):
    doc = upload_and_wait_parsed(api_client, sample_docx_path)
    yield doc
    api_client.delete(f"/api/v1/documents/{doc['id']}")


@pytest.fixture(scope="module")
def analyzed_document(api_client, sample_docx_path):
    doc = upload_and_wait_parsed(api_client, sample_docx_path)
    doc_id = doc["id"]

    response = api_client.post(
        f"/api/v1/analysis/{doc_id}/start",
        json={"mode": "economic"},
    )
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
