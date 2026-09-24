"""Fase 1: retrieval_run, corpus_version, citação no servidor e parecer."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.models.retrieval import RetrievalRun
from app.schemas.chat import ChatCitation
from app.services.analyzer.parecer_origins import append_parecer_origins
from app.services.chat.sources import hydrate_citations
from app.services.chat.validator import validate_llm_answer
from app.services.rag.corpus_version import (
    clear_corpus_version_cache,
    compute_corpus_version,
    hash_manifest,
)
from app.services.rag.retrieval_log import record_retrieval_run
from app.services.rag.retriever import RetrievedChunk


def _run(coro):
    return asyncio.run(coro)


def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_create())
    return async_sessionmaker(engine, expire_on_commit=False)


def test_hash_manifest_estavel_e_ordenado():
    a = hash_manifest(
        [{"law_number": "B", "version": "1", "total_chunks": 2}]
    )
    b = hash_manifest(
        [{"total_chunks": 2, "version": "1", "law_number": "B"}]
    )
    assert a == b
    other = hash_manifest(
        [{"law_number": "A", "version": "1", "total_chunks": 1}]
    )
    assert a != other


def test_compute_corpus_version_persiste_hash():
    Session = _session()
    clear_corpus_version_cache()

    async def _cenario():
        async with Session() as db:
            db.add(
                LegalDocument(
                    law_number="Lei 14.133/2021",
                    law_title="Licitações",
                    version="v-test",
                    total_chunks=1,
                )
            )
            await db.commit()
            first, manifest = await compute_corpus_version(db)
            clear_corpus_version_cache()
            second, _ = await compute_corpus_version(db)
            return first, second, manifest

    first, second, manifest = _run(_cenario())
    assert first == second
    assert len(first) == 64
    assert manifest[0]["law_number"] == "Lei 14.133/2021"


def test_record_retrieval_run_grava_ids_ordenados():
    Session = _session()
    clear_corpus_version_cache()
    chunk_id = str(uuid.uuid4())

    async def _cenario():
        async with Session() as db:
            chunks = [
                RetrievedChunk(
                    id=chunk_id,
                    law_number="Lei 14.133/2021",
                    law_title="Licitações",
                    article="art. 5º",
                    section="",
                    text="A contratação observará os princípios.",
                    score=0.91,
                )
            ]
            run = await record_retrieval_run(
                db,
                operation_type="analysis",
                query="princípios da contratação",
                chunks=chunks,
                params={"top_k": 4},
            )
            await db.commit()
            stored = (
                await db.execute(select(RetrievalRun).where(RetrievalRun.id == run.id))
            ).scalar_one()
            return stored

    stored = _run(_cenario())
    assert stored.operation_type == "analysis"
    assert stored.retrieved_ids == [chunk_id]
    assert stored.scores[0]["id"] == chunk_id
    assert stored.corpus_version
    assert stored.query_hash


def test_hydrate_citations_usa_texto_do_servidor():
    catalog = [
        ChatCitation(
            type="legal",
            source_id="legal:1",
            reference="Lei 14.133/2021, art. 5º",
            title="Lei 14.133/2021",
            snippet="Texto canônico do banco.",
        )
    ]
    llm = [
        ChatCitation(
            type="legal",
            source_id="legal:1",
            reference="Inventado pelo modelo",
            title="Título falso",
            snippet="Snippet alucinado.",
        )
    ]
    hidratadas = hydrate_citations(llm, catalog)
    assert hidratadas[0].reference == "Lei 14.133/2021, art. 5º"
    assert hidratadas[0].snippet == "Texto canônico do banco."
    assert hidratadas[0].title == "Lei 14.133/2021"


def test_source_id_fora_do_contexto_e_rejeitado():
    raw = (
        '{"refused": false, "answer": "fato jurídico", "grounded": true, '
        '"citations": [{"type": "legal", "source_id": "legal:999"}]}'
    )
    resultado = validate_llm_answer(
        raw,
        require_grounding=True,
        valid_source_ids={"legal:1"},
    )
    assert resultado.refused is True
    assert resultado.reason == "source-id-inexistente"
    assert resultado.citations == []


def test_parecer_aponta_correcoes_e_recuperacoes():
    texto = append_parecer_origins(
        "Parecer base.",
        ["corr-1", "corr-2"],
        ["run-a"],
    )
    assert texto.startswith("Parecer base.")
    assert "corr-1" in texto
    assert "corr-2" in texto
    assert "run-a" in texto
