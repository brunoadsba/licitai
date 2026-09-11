"""E2E fast: proposta não inicia análise de TR; modes economic/multi_agent."""

from __future__ import annotations

import pytest

from helpers import upload_and_wait_parsed

pytestmark = pytest.mark.e2e_fast


def test_proposta_upload_requires_fornecedor(api_client, sample_docx_path):
    with open(sample_docx_path, "rb") as f:
        resp = api_client.post(
            "/api/v1/documents/upload",
            data={"document_type": "proposta"},
            files={
                "file": (
                    "sample-tr.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 400


def test_proposta_cannot_start_analysis(api_client, sample_docx_path):
    forn = api_client.post(
        "/api/v1/fornecedores",
        json={"nome": "E2E Proposta Guard", "email": None, "cnpj": None},
    )
    assert forn.status_code == 201, forn.text
    forn_id = forn.json()["id"]
    try:
        doc = upload_and_wait_parsed(
            api_client,
            sample_docx_path,
            document_type="proposta",
            fornecedor_id=forn_id,
        )
        assert doc["document_type"] == "proposta"
        start = api_client.post(
            f"/api/v1/analysis/{doc['id']}/start",
            json={"mode": "economic"},
        )
        assert start.status_code == 400, start.text
        assert "Termos de Referência" in start.json().get("detail", "")
    finally:
        api_client.delete(f"/api/v1/documents/{doc['id']}")
        api_client.delete(f"/api/v1/fornecedores/{forn_id}")


def test_start_analysis_modes(api_client, uploaded_document):
    doc_id = uploaded_document["id"]
    for mode in ("economic", "multi_agent"):
        resp = api_client.post(
            f"/api/v1/analysis/{doc_id}/start",
            json={"mode": mode},
        )
        # 202 nova, ou 409 se ainda running da tentativa anterior
        assert resp.status_code in (202, 409), resp.text
        if resp.status_code == 202:
            analysis_id = resp.json()["analysis_id"]
            detail = api_client.get(f"/api/v1/analysis/{analysis_id}")
            assert detail.status_code == 200
            assert detail.json()["analysis_mode"] == mode
            break
