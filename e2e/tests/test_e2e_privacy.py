"""E2E fast: política fail-closed na borda HTTP (sem LLM)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e_fast

_SIGILOSO_DETAIL = "sigiloso ou sem classificação"


def test_upload_sem_classificacao_retorna_422(api_client, sample_docx_path):
    with open(sample_docx_path, "rb") as f:
        resp = api_client.post(
            "/api/v1/documents/upload",
            data={"document_type": "tr"},
            files={
                "file": (
                    "sample-tr.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 422, resp.text
    assert _SIGILOSO_DETAIL in resp.json().get("detail", "").lower()


def test_upload_sigiloso_retorna_422(api_client, sample_docx_path):
    with open(sample_docx_path, "rb") as f:
        resp = api_client.post(
            "/api/v1/documents/upload",
            data={"document_type": "tr", "classification": "sigiloso"},
            files={
                "file": (
                    "sample-tr.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 422, resp.text
    assert _SIGILOSO_DETAIL in resp.json().get("detail", "").lower()


def test_gerador_sem_classificacao_retorna_422(api_client):
    resp = api_client.post(
        "/api/v1/generator/tr",
        json={
            "tipo_contratacao": "compras_gerais",
            "objeto": "Aquisição de cadeiras para a unidade administrativa.",
            "justificativa": "Necessidade de repor o mobiliário da unidade.",
            "prazo_meses": 12,
            "criterio_julgamento": "menor_preco",
        },
    )
    assert resp.status_code == 422, resp.text
    assert _SIGILOSO_DETAIL in resp.json().get("detail", "").lower()


def test_chat_livre_sem_classificacao_retorna_422(api_client):
    resp = api_client.post("/api/v1/chat/conversations", json={})
    assert resp.status_code == 422, resp.text
    assert _SIGILOSO_DETAIL in resp.json().get("detail", "").lower()
