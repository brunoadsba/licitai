"""E2E fast: fornecedores e moldes."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.e2e_fast

MIN_MOLDE = {
    "versao": 1,
    "regras": [
        {
            "id": "e2e_vigencia",
            "rotulo": "Vigência E2E",
            "tipo": "numero_inteiro",
            "ancora": "vigência",
            "unidade": "dias",
        }
    ],
}


def test_fornecedor_crud(api_client):
    create = api_client.post(
        "/api/v1/fornecedores",
        json={"nome": "E2E Fornecedor", "email": "e2e@example.com", "cnpj": None},
    )
    assert create.status_code == 201, create.text
    fid = create.json()["id"]
    try:
        listed = api_client.get("/api/v1/fornecedores")
        assert listed.status_code == 200
        assert any(f["id"] == fid for f in listed.json()["fornecedores"])
        got = api_client.get(f"/api/v1/fornecedores/{fid}")
        assert got.status_code == 200
        assert got.json()["nome"] == "E2E Fornecedor"
    finally:
        deleted = api_client.delete(f"/api/v1/fornecedores/{fid}")
        assert deleted.status_code == 204


def test_molde_create_and_list(api_client):
    create = api_client.post(
        "/api/v1/moldes",
        json={
            "nome": "Molde E2E Temp",
            "descricao": "teste",
            "config_json": json.dumps(MIN_MOLDE, ensure_ascii=False),
        },
    )
    assert create.status_code == 201, create.text
    mid = create.json()["id"]
    try:
        listed = api_client.get("/api/v1/moldes")
        assert listed.status_code == 200
        assert any(m["id"] == mid for m in listed.json()["moldes"])
    finally:
        deleted = api_client.delete(f"/api/v1/moldes/{mid}")
        assert deleted.status_code in (204, 200, 409)
