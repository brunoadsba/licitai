"""
Testes do retriever RAG (Fase 4 — busca semântica e fallback textual).

Usa banco SQLite em memória com chunks de lei e embeddings fake (provedor
fake implementando a interface EmbeddingsProvider — permitido em testes).
"""

import asyncio
import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.retriever import (
    retrieve,
    _cosseno,
    _para_chunks,
)
from app.services.rag.loader import build_fts_index


# Vetores determinísticos: cada texto "relevante" mapeia para um vetor fixo.
VETORES_QUERY = {
    "garantia de execucao": [1.0, 0.0, 0.0],
    "instrucoes de seguranca": [0.0, 1.0, 0.0],
}


class FakeEmbeddingsProvider:
    """Provedor fake de embeddings (implementa a interface real)."""

    provider_name = "fake"
    model_name = "fake-emb"

    async def embed(self, text: str) -> list[float]:
        return VETORES_QUERY.get(text.strip(), [1.0, 0.0, 0.0])

    async def health_check(self) -> bool:
        return True


def _run(coroutine):
    return asyncio.run(coroutine)


async def _seed_sem_embeddings() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        doc = LegalDocument(
            law_number="Lei 14.133/2021",
            law_title="Licitações",
        )
        db.add(doc)
        await db.flush()
        db.add_all([
            LegalChunk(
                legal_document_id=doc.id, chunk_index=0,
                article="Art. 6º",
                chunk_text="Garantia de execução exigida no edital.",
            ),
            LegalChunk(
                legal_document_id=doc.id, chunk_index=1,
                article="Art. 28º",
                chunk_text="Instruções de segurança do trabalho.",
            ),
        ])
        await build_fts_index(db)
        await db.commit()
    return Session


async def _seed_com_embeddings() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        doc = LegalDocument(
            law_number="Lei 14.133/2021",
            law_title="Licitações",
        )
        db.add(doc)
        await db.flush()
        db.add_all([
            LegalChunk(
                legal_document_id=doc.id, chunk_index=0,
                article="Art. 6º",
                chunk_text="Garantia de execução exigida no edital.",
                embedding=json.dumps([1.0, 0.0, 0.0]),
            ),
            LegalChunk(
                legal_document_id=doc.id, chunk_index=1,
                article="Art. 28º",
                chunk_text="Instruções de segurança do trabalho.",
                embedding=json.dumps([0.0, 1.0, 0.0]),
            ),
            LegalChunk(
                legal_document_id=doc.id, chunk_index=2,
                article="Art. 40º",
                chunk_text="Da garantia complementar.",
                embedding=json.dumps([0.8, 0.6, 0.0]),
            ),
        ])
        await build_fts_index(db)
        await db.commit()
    return Session


def test_cosseno_basico():
    assert _cosseno([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert _cosseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert _cosseno([1.0, 0.0], [0.0, 0.0]) == 0.0


def test_para_chunks_converte_linhas():
    rows = [
        {"law_number": "Lei X", "law_title": "T", "article": "Art. 1º",
         "section": "", "chunk_text": "texto", "score": 0.9},
    ]
    chunks = _para_chunks(rows)
    assert chunks[0].law_number == "Lei X"
    assert chunks[0].score == pytest.approx(0.9)


def test_retrieve_semantico_ranqueia_por_similaridade(monkeypatch):
    monkeypatch.setattr(
        "app.services.rag.retriever.get_embeddings_provider",
        lambda: FakeEmbeddingsProvider(),
    )

    async def _cenario():
        Session = await _seed_com_embeddings()
        async with Session() as db:
            return await retrieve(db, "garantia de execução", top_k=2)

    chunks = _run(_cenario())
    # Mais similar: Art. 6º (cosseno 1.0) e Art. 40º (0.8)
    assert [c.article for c in chunks] == ["Art. 6º", "Art. 40º"]
    assert chunks[0].score > chunks[1].score
    assert chunks[1].article == "Art. 40º"


def test_retrieve_fallback_textual_sem_embeddings():
    async def _cenario():
        Session = await _seed_sem_embeddings()
        async with Session() as db:
            return await retrieve(db, "instruções de segurança", top_k=2)

    chunks = _run(_cenario())
    assert any(c.article == "Art. 28º" for c in chunks)


def test_retrieve_fallback_quando_provider_falha(monkeypatch):
    class ProviderQueFalha(FakeEmbeddingsProvider):
        async def embed(self, text: str) -> list[float]:
            raise RuntimeError("API indisponível")

    monkeypatch.setattr(
        "app.services.rag.retriever.get_embeddings_provider",
        lambda: ProviderQueFalha(),
    )

    async def _cenario():
        Session = await _seed_com_embeddings()
        async with Session() as db:
            return await retrieve(db, "instruções de segurança", top_k=2)

    chunks = _run(_cenario())
    # Mesmo com embeddings no banco, a falha do provedor não quebra a busca
    assert any(c.article == "Art. 28º" for c in chunks)


def test_retrieve_vazio_para_query_vazia():
    async def _cenario():
        Session = await _seed_com_embeddings()
        async with Session() as db:
            return await retrieve(db, "   ")

    assert _run(_cenario()) == []
