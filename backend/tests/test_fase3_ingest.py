"""Ingestão Fase 3: hash estável, idempotência e falha reprocessável."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.document import Document
from app.models.job import Job
from app.models.legal import LegalChunk, LegalDocument
from app.services.ingest.hashing import sha256_text
from app.services.ingest.pipeline import ingest_legal_source
from app.services.upload_service import enqueue_document_parse


LAW = (
    "Art. 1º A licitação observa a isonomia.\n"
    "Art. 2º O edital define o objeto.\n"
)


def _session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine


def test_hash_estavel():
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abd")
    assert len(sha256_text("abc")) == 64


def test_duas_corridas_mesmo_estado_logico():
    async def _run():
        engine = _session_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            first = await ingest_legal_source(
                db,
                content=LAW,
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://www.planalto.gov.br/l14133",
                origin="planalto",
            )
            ids_before = set(
                (
                    await db.execute(
                        select(LegalChunk.id).where(
                            LegalChunk.legal_document_id == first.document.id
                        )
                    )
                ).scalars().all()
            )
            second = await ingest_legal_source(
                db,
                content=LAW,
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://www.planalto.gov.br/l14133",
                origin="planalto",
            )
            await db.commit()
            docs = (await db.execute(select(LegalDocument))).scalars().all()
            ids_after = set(
                (await db.execute(select(LegalChunk.id))).scalars().all()
            )
            return first, second, docs, ids_before, ids_after

    first, second, docs, ids_before, ids_after = asyncio.run(_run())
    assert first.success and second.success
    assert second.unchanged is True
    assert first.document.id == second.document.id
    assert first.document.content_hash == second.document.content_hash
    assert first.manifest.source_hash == sha256_text(LAW)
    assert len(docs) == 1
    assert ids_before == ids_after
    assert docs[0].ingest_status == "published"
    assert docs[0].origin == "planalto"


def test_falha_incompleta_e_reprocessavel():
    async def _run():
        engine = _session_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            failed = await ingest_legal_source(
                db,
                content="Preâmbulo sem artigo publicado.",
                law_number="Lei 99.999/2099",
                law_title="Incompleta",
                origin="fixture",
            )
            failed_status = failed.document.ingest_status
            failed_error = failed.document.last_error
            retry = await ingest_legal_source(
                db,
                content=LAW,
                law_number="Lei 99.999/2099",
                law_title="Incompleta",
                origin="fixture",
            )
            await db.commit()
            chunks = (
                await db.execute(
                    select(LegalChunk).where(
                        LegalChunk.legal_document_id == retry.document.id
                    )
                )
            ).scalars().all()
            return failed, failed_status, failed_error, retry, chunks

    failed, failed_status, failed_error, retry, chunks = asyncio.run(_run())
    assert failed.success is False
    assert failed.published is False
    assert failed_status == "failed"
    assert failed_error
    assert retry.success is True
    assert retry.document.id == failed.document.id
    assert retry.document.ingest_status == "published"
    assert retry.document.last_error is None
    assert len(chunks) == 2


def test_enqueue_parse_nao_executa_extracao():
    async def _run():
        engine = _session_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            document = Document(
                filename_original="tr.pdf",
                filename_stored="tr-stored.pdf",
                file_type="pdf",
                file_size_bytes=120,
                document_type="tr",
                status="uploaded",
            )
            db.add(document)
            await db.flush()
            first = await enqueue_document_parse(db, document)
            second = await enqueue_document_parse(db, document)
            await db.commit()
            jobs = (await db.execute(select(Job))).scalars().all()
            return document.id, first.id, second.id, jobs

    doc_id, job_a, job_b, jobs = asyncio.run(_run())
    assert job_a == job_b
    assert len(jobs) == 1
    assert jobs[0].type == "parse"
    assert jobs[0].payload["document_id"] == str(doc_id)
    assert jobs[0].status == "pending"
