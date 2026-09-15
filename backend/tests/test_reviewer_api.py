"""Testes da API do revisor-assistente."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_review_suggestions_404_analise_inexistente(monkeypatch):
    async def fake_load(db, aid):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    monkeypatch.setattr("app.api.reviewer._load_analysis", fake_load)
    c = TestClient(app, raise_server_exceptions=True)
    fake = str(uuid.uuid4())
    r = c.get(f"/api/v1/analysis/{fake}/review-suggestions")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_review_suggestions_lista_com_mock(monkeypatch):
    from app.api.reviewer import list_review_suggestions

    class FakeCorr:
        id = uuid.uuid4()
        document_item_id = uuid.uuid4()
        original_text = "texto original presente"
        suggested_text = "texto corrigido"
        legal_basis = "Lei 14.133/2021, art. 6"
        severity = "medio"
        importance = "media"
        category = "tecnica"
        review_status = "pendente"

    fake_analysis = type("A", (), {"id": uuid.uuid4(), "corrections": [FakeCorr()], "document": type("D", (), {"items": []})()})()

    async def fake_load(db, aid):
        return fake_analysis, {str(FakeCorr.document_item_id): "texto original presente no item"}

    async def fake_refs(db):
        return {"14.133/2021|6"}

    monkeypatch.setattr("app.api.reviewer._load_analysis", fake_load)
    monkeypatch.setattr("app.api.reviewer.get_valid_legal_refs", fake_refs)

    async def _fake_refine(s, **kw):
        return s

    monkeypatch.setattr("app.api.reviewer.refine_with_llm", _fake_refine)

    from sqlalchemy.ext.asyncio import AsyncSession

    class FakeDB:
        pass

    resp = await list_review_suggestions(fake_analysis.id, pending_only=True, db=FakeDB())  # type: ignore[arg-type]
    assert resp.total == 1
    assert len(resp.suggestions) == 1
    assert resp.suggestions[0].suggestion in ("aprovar", "rejeitar", "ajustar")
