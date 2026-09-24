"""Persistência idempotente de documentos jurídicos (mantém o mesmo id)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalChunk, LegalDocument
from app.services.ingest.schema import IngestManifest
from app.services.rag.corpus_version import clear_corpus_version_cache
from app.services.rag.retriever import _clear_legal_context_cache
from app.services.rag.loader import LawChunk

STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"


async def get_legal_document(
    db: AsyncSession, law_number: str
) -> LegalDocument | None:
    result = await db.execute(
        select(LegalDocument).where(LegalDocument.law_number == law_number)
    )
    return result.scalar_one_or_none()


async def persist_legal_document(
    db: AsyncSession,
    *,
    chunks: list[LawChunk],
    law_number: str,
    law_title: str,
    source_url: str | None,
    version: str | None,
    content_hash: str,
    origin: str | None,
    collected_at: datetime | None,
    ingest_status: str,
    last_error: str | None,
    manifest: IngestManifest,
) -> tuple[LegalDocument, bool]:
    """Grava ou atualiza. Retorna (documento, unchanged)."""
    existing = await get_legal_document(db, law_number)

    if (
        existing
        and ingest_status == STATUS_PUBLISHED
        and existing.ingest_status == STATUS_PUBLISHED
        and existing.content_hash == content_hash
    ):
        return existing, True

    if ingest_status == STATUS_FAILED:
        return await _persist_failure(
            db,
            existing=existing,
            law_number=law_number,
            law_title=law_title,
            source_url=source_url,
            version=version,
            content_hash=content_hash,
            origin=origin,
            collected_at=collected_at,
            last_error=last_error,
            manifest=manifest,
        ), False

    doc = existing or LegalDocument(law_number=law_number, law_title=law_title)
    if existing:
        await db.execute(
            delete(LegalChunk).where(LegalChunk.legal_document_id == existing.id)
        )
    else:
        db.add(doc)
        await db.flush()

    _apply_metadata(
        doc,
        law_title=law_title,
        source_url=source_url,
        version=version,
        content_hash=content_hash,
        origin=origin,
        collected_at=collected_at,
        ingest_status=STATUS_PUBLISHED,
        last_error=None,
        manifest=manifest,
        total_chunks=len(chunks),
    )
    _add_chunks(db, doc, chunks, law_number, law_title, manifest)
    await db.flush()
    clear_corpus_version_cache()
    _clear_legal_context_cache()
    return doc, False


async def _persist_failure(
    db: AsyncSession,
    *,
    existing: LegalDocument | None,
    law_number: str,
    law_title: str,
    source_url: str | None,
    version: str | None,
    content_hash: str,
    origin: str | None,
    collected_at: datetime | None,
    last_error: str | None,
    manifest: IngestManifest,
) -> LegalDocument:
    if existing and existing.ingest_status == STATUS_PUBLISHED:
        existing.last_error = last_error
        await db.flush()
        return existing

    doc = existing or LegalDocument(law_number=law_number, law_title=law_title)
    if existing:
        await db.execute(
            delete(LegalChunk).where(LegalChunk.legal_document_id == existing.id)
        )
    else:
        db.add(doc)
        await db.flush()

    _apply_metadata(
        doc,
        law_title=law_title,
        source_url=source_url,
        version=version,
        content_hash=content_hash,
        origin=origin,
        collected_at=collected_at,
        ingest_status=STATUS_FAILED,
        last_error=last_error,
        manifest=manifest,
        total_chunks=0,
    )
    await db.flush()
    clear_corpus_version_cache()
    _clear_legal_context_cache()
    return doc


def _apply_metadata(
    doc: LegalDocument,
    *,
    law_title: str,
    source_url: str | None,
    version: str | None,
    content_hash: str,
    origin: str | None,
    collected_at: datetime | None,
    ingest_status: str,
    last_error: str | None,
    manifest: IngestManifest,
    total_chunks: int,
) -> None:
    doc.law_title = law_title
    doc.source_url = source_url
    doc.version = version
    doc.content_hash = content_hash
    doc.origin = origin
    doc.collected_at = collected_at
    doc.ingest_status = ingest_status
    doc.last_error = last_error
    doc.ingest_manifest = manifest.model_dump(mode="json")
    doc.total_chunks = total_chunks


def _add_chunks(
    db: AsyncSession,
    doc: LegalDocument,
    chunks: list[LawChunk],
    law_number: str,
    law_title: str,
    manifest: IngestManifest,
) -> None:
    marks_dump = [m.model_dump() for m in manifest.marks]
    for idx, chunk in enumerate(chunks):
        meta: dict = {
            "law_number": law_number,
            "law_title": law_title,
            "article": chunk.article,
            "status": "vigente",
        }
        if chunk.page is not None:
            meta["page"] = chunk.page
        scoped = [
            m
            for m in marks_dump
            if m["kind"] == "redacao_dada" and m["text"] in chunk.text
        ]
        if scoped:
            meta["marks"] = scoped
        db.add(
            LegalChunk(
                legal_document_id=doc.id,
                chunk_index=idx,
                article=chunk.article,
                section=chunk.section,
                chunk_text=chunk.text,
                doc_metadata=meta,
            )
        )
