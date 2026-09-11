"""E2E fast: diff entre dois TRs."""

from __future__ import annotations

import pytest

from helpers import upload_and_wait_parsed

pytestmark = pytest.mark.e2e_fast


def test_documents_diff(api_client, sample_docx_path):
    a = upload_and_wait_parsed(api_client, sample_docx_path)
    b = upload_and_wait_parsed(api_client, sample_docx_path)
    try:
        resp = api_client.post(
            "/api/v1/documents/diff",
            json={
                "documento_antigo_id": a["id"],
                "documento_novo_id": b["id"],
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "itens" in body
        assert "resumo" in body
        assert body["total"] >= 0
    finally:
        api_client.delete(f"/api/v1/documents/{a['id']}")
        api_client.delete(f"/api/v1/documents/{b['id']}")
