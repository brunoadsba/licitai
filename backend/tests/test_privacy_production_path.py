"""Caminho de produção da política de sigilo.

Garante que análise, job, RAG, chat, revisor e gerador não chamam Groq/Gemini
quando o documento é sigiloso ou está sem classificação.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registra tabelas
from app.config import Settings, settings
from app.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis
from app.models.document import Document, DocumentItem
from app.models.job import Job
from app.models.legal import LegalChunk, LegalDocument
from app.services.analyzer.engine import run_analysis
from app.services.jobs.queue import STATUS_FAILED, enqueue
from app.services.llm.factory import get_llm_provider_for, reset_llm_provider
from app.services.privacy import PrivacyPolicyError, resolve_policy
from app.services.rag.loader import build_fts_index
from app.services.rag.retriever import _clear_legal_context_cache, retrieve
from app.services.reviewer.second_opinion import refine_with_llm

CANARY = "texto-canario-de-sigilo"
_ENGINES: list = []


async def _factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _ENGINES.append(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def _lock_cloud(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_allow_cloud", False)
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "chat_force_fake_provider", False)
    reset_llm_provider()


def _document(**overrides) -> Document:
    data = dict(
        filename_original="tr.pdf",
        filename_stored=f"{uuid.uuid4()}.pdf",
        file_type="pdf",
        file_size_bytes=1200,
        document_type="tr",
        status="parsed",
        classification=None,
    )
    data.update(overrides)
    return Document(**data)


def _item(document_id) -> DocumentItem:
    return DocumentItem(
        document_id=document_id,
        item_number="1.1",
        title="Objeto",
        content=(
            f"{CANARY} A contratação deverá observar os requisitos técnicos "
            "e jurídicos estabelecidos neste termo de referência."
        ),
        item_order=1,
        item_type="item",
    )


class _SpyLLM:
    provider_name = "fake"
    model_name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return json.dumps(
            {
                "answer": "Resposta pública de teste.",
                "grounded": True,
                "confidence": 0.9,
                "citations": [],
                "suggested_actions": [],
            }
        )


def _cliente(Session, llm=None):
    async def override_get_db():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    if llm is not None:
        from app.services.chat.llm_adapter import get_chat_llm

        app.dependency_overrides[get_chat_llm] = lambda: llm
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture(autouse=True)
async def _limpa_overrides():
    yield
    app.dependency_overrides.clear()
    from app.services.llm import factory as factory_mod

    local = factory_mod._local_llm_provider_instance
    inner = getattr(local, "_inner", None)
    client = getattr(inner, "_client", None)
    if client is not None:
        await client.aclose()
    reset_llm_provider()
    while _ENGINES:
        engine = _ENGINES.pop()
        await engine.dispose()


def test_override_cloud_rejeitado_fora_de_development():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            llm_allow_cloud=True,
            api_token="tok",
            database_url="postgresql+asyncpg://u:p@localhost/db",
        )


def test_default_allow_cloud_false(monkeypatch):
    monkeypatch.delenv("LLM_ALLOW_CLOUD", raising=False)
    carregado = Settings(_env_file=None, app_env="development")
    assert carregado.llm_allow_cloud is False


def test_publico_continua_na_nuvem_sem_flag(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    policy = resolve_policy("publico")
    assert policy.cloud_llm is True
    assert policy.cloud_embeddings is True

    spy = _SpyLLM()
    import app.services.llm.factory as factory_mod

    original = factory_mod.get_llm_provider
    factory_mod.get_llm_provider = lambda: spy  # type: ignore[assignment]
    try:
        provedor = get_llm_provider_for(policy, document_id="doc-publico")
        assert asyncio.run(provedor.generate("s", "u"))
    finally:
        factory_mod.get_llm_provider = original
    assert spy.calls == 1
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_ollama_sigiloso_nao_faz_failover(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    monkeypatch.setattr(settings, "llm_provider", "ollama")

    async def _ollama_fora(self, system_prompt, user_prompt):
        raise RuntimeError("ollama indisponivel")

    monkeypatch.setattr(
        "app.services.llm.ollama_provider.OllamaProvider.generate",
        _ollama_fora,
    )
    provedor = get_llm_provider_for(resolve_policy("sigiloso"), document_id="d1")
    with pytest.raises(RuntimeError, match="ollama"):
        await provedor.generate("sistema", "consulta")
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_analise_sigilosa_nao_chama_nuvem(
    monkeypatch, guard_against_cloud, caplog
):
    _lock_cloud(monkeypatch)
    caplog.set_level(logging.INFO)
    Session = await _factory()
    async with Session() as db:
        doc = _document(classification="sigiloso")
        db.add(doc)
        await db.flush()
        db.add(_item(doc.id))
        analysis = Analysis(
            document_id=doc.id,
            status="pending",
            llm_provider="groq",
            llm_model="test",
            analysis_mode="economic",
        )
        db.add(analysis)
        await db.commit()
        with pytest.raises(PrivacyPolicyError):
            await run_analysis(db, analysis.id, doc.id)
        fresh = await db.get(Analysis, analysis.id)
        assert fresh is not None
        assert fresh.status == "error"
        assert fresh.llm_provider == "blocked"
        assert "sigiloso" in (fresh.error_message or "").lower()
    assert guard_against_cloud == []
    assert CANARY not in caplog.text
    assert "privacy.decision" in caplog.text
    assert "blocked" in caplog.text


@pytest.mark.asyncio
async def test_job_null_falha_sem_retry(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    Session = await _factory()
    monkeypatch.setattr("app.services.jobs.handlers.async_session_factory", Session)
    monkeypatch.setattr("app.worker.async_session_factory", Session)

    async with Session() as db:
        doc = _document(classification=None)
        db.add(doc)
        await db.flush()
        db.add(_item(doc.id))
        analysis = Analysis(
            document_id=doc.id,
            status="pending",
            llm_provider="groq",
            llm_model="test",
            analysis_mode="economic",
        )
        db.add(analysis)
        await db.flush()
        job = await enqueue(
            db,
            "analysis",
            {"analysis_id": str(analysis.id), "document_id": str(doc.id)},
        )
        await db.commit()
        job_id, analysis_id = job.id, analysis.id
        payload = dict(job.payload or {})

    from app.worker import _JobRef, process_job

    await process_job(_JobRef(id=job_id, type="analysis", payload=payload))

    async with Session() as db:
        job_db = await db.get(Job, job_id)
        analysis_db = await db.get(Analysis, analysis_id)
        assert job_db is not None and job_db.status == STATUS_FAILED
        assert analysis_db is not None and analysis_db.status == "error"
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_reanalise_null_retorna_422_sem_job(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    Session = await _factory()
    async with Session() as db:
        doc = _document(classification=None)
        db.add(doc)
        await db.flush()
        analysis = Analysis(
            document_id=doc.id,
            status="completed",
            llm_provider="groq",
            llm_model="test",
            analysis_mode="economic",
            run_snapshot={"failed_item_ids": [str(uuid.uuid4())]},
        )
        db.add(analysis)
        await db.commit()
        analysis_id = analysis.id

    async with _cliente(Session) as client:
        response = await client.post(
            f"/api/v1/analysis/{analysis_id}/reanalyze-partial"
        )
    assert response.status_code == 422
    assert "sigiloso" in response.text.lower() or "classifica" in response.text.lower()

    async with Session() as db:
        jobs = (await db.execute(select(Job))).scalars().all()
        assert jobs == []
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_retrieve_restrito_nao_embeda(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    monkeypatch.setattr(settings, "rag_rerank_mode", "llm")
    _clear_legal_context_cache()
    emb_calls = {"n": 0}

    class _Emb:
        provider_name = "gemini"
        model_name = "fake"

        async def embed(self, text: str) -> list[float]:
            emb_calls["n"] += 1
            return [1.0, 0.0, 0.0]

    monkeypatch.setattr(
        "app.services.rag.retriever.get_embeddings_provider",
        lambda: _Emb(),
    )
    Session = await _factory()
    async with Session() as db:
        law = LegalDocument(law_number="Lei 14.133/2021", law_title="Licitações")
        db.add(law)
        await db.flush()
        db.add(
            LegalChunk(
                legal_document_id=law.id,
                chunk_index=0,
                article="Art. 6º",
                chunk_text="Garantia de execução exigida no edital.",
                embedding=json.dumps([1.0, 0.0, 0.0]),
            )
        )
        await build_fts_index(db)
        await db.commit()
        rerank = _SpyLLM()
        chunks = await retrieve(
            db,
            "garantia de execução",
            top_k=2,
            allow_semantic=False,
            allow_llm_rerank=False,
            llm=rerank,
        )
    assert chunks
    assert emb_calls["n"] == 0
    assert rerank.calls == 0
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_chat_sigiloso_bloqueia_e_publico_passa(
    monkeypatch, guard_against_cloud
):
    _lock_cloud(monkeypatch)
    Session = await _factory()
    async with Session() as db:
        sigiloso = _document(classification="sigiloso")
        publico = _document(classification="publico")
        db.add_all([sigiloso, publico])
        await db.commit()
        sig_id, pub_id = str(sigiloso.id), str(publico.id)

    spy = _SpyLLM()
    pergunta = "Qual o fundamento legal da exigência de garantia neste objeto?"
    async with _cliente(Session, spy) as client:
        bloqueada = await client.post(
            "/api/v1/chat/conversations",
            json={"document_id": sig_id, "classification": "publico"},
        )
        assert bloqueada.status_code == 422
        assert spy.calls == 0

        livre = await client.post("/api/v1/chat/conversations", json={})
        assert livre.status_code == 422
        resp = livre

        ok = await client.post(
            "/api/v1/chat/conversations",
            json={"document_id": pub_id},
        )
        assert ok.status_code == 201
        ok_resp = await client.post(
            f"/api/v1/chat/conversations/{ok.json()['id']}/messages",
            json={"content": pergunta},
        )
        assert ok_resp.status_code == 200
        assert spy.calls == 1
    assert guard_against_cloud == []
    assert CANARY not in resp.text


@pytest.mark.asyncio
async def test_revisor_sigiloso_nao_chama_nuvem(monkeypatch, guard_against_cloud):
    _lock_cloud(monkeypatch)
    monkeypatch.setenv("REVIEWER_SECOND_OPINION", "1")
    suggestion = SimpleNamespace(
        correction_id="c",
        suggestion="aprovar",
        confidence=0.5,
        reason="motivo determinístico",
    )
    correction = SimpleNamespace(problem="problema", suggested_text="texto")
    result = await refine_with_llm(
        suggestion,
        correction=correction,
        item_content=f"{CANARY} trecho do item sigiloso.",
        classification="sigiloso",
    )
    assert guard_against_cloud == []
    assert result.reason == "motivo determinístico"


@pytest.mark.asyncio
async def test_gerador_sem_classificacao_retorna_422(
    monkeypatch, guard_against_cloud
):
    _lock_cloud(monkeypatch)
    Session = await _factory()
    async with _cliente(Session) as client:
        response = await client.post(
            "/api/v1/generator/tr",
            json={
                "tipo_contratacao": "compras_gerais",
                "objeto": "Aquisição de equipamentos de informática para a unidade.",
                "justificativa": "Necessidade de renovar o parque computacional da unidade.",
                "prazo_meses": 12,
                "criterio_julgamento": "menor_preco",
            },
        )
    assert response.status_code == 422
    assert guard_against_cloud == []


@pytest.mark.asyncio
async def test_backfill_dry_run_e_so_null(monkeypatch):
    from scripts.backfill_classification import backfill_classification

    Session = await _factory()
    async with Session() as db:
        nulo = _document(classification=None)
        marcado = _document(classification="publico")
        db.add_all([nulo, marcado])
        await db.commit()
        nulo_id, marcado_id = nulo.id, marcado.id

        seco = await backfill_classification(
            db, to="interno", ids=None, all_null=True, apply=False
        )
        assert str(nulo_id) in seco
        await db.refresh(nulo)
        assert nulo.classification is None

        aplicados = await backfill_classification(
            db, to="interno", ids=[str(nulo_id), str(marcado_id)], all_null=False, apply=True
        )
        assert aplicados == [str(nulo_id)]
        await db.refresh(nulo)
        await db.refresh(marcado)
        assert nulo.classification == "interno"
        assert marcado.classification == "publico"
