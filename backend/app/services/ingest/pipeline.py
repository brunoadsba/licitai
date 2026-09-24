"""Pipeline: source → extract → normalize → validate → version → index."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingest.hashing import sha256_text
from app.services.ingest.persist import persist_legal_document
from app.services.ingest.schema import IngestManifest, IngestResult
from app.services.parser.legal_marks import normalize_legal_text
from app.services.rag.loader import (
    build_fts_index,
    parse_extra_text,
    parse_law_text,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def ingest_legal_source(
    db: AsyncSession,
    *,
    content: str,
    law_number: str,
    law_title: str,
    source_url: str | None = None,
    version: str | None = None,
    origin: str | None = None,
    collected_at: datetime | None = None,
    require_articles: bool = True,
    extractor: str = "text",
) -> IngestResult:
    """Ingesta com estágios separados; falha não publica rascunho incompleto."""
    collected = collected_at or _now()
    source_hash = sha256_text(content)
    extracted = content
    normalized = normalize_legal_text(extracted)
    normalized_hash = sha256_text(normalized.vigente)
    manifest = IngestManifest(
        origin=origin,
        source_url=source_url,
        collected_at=collected,
        source_hash=source_hash,
        normalized_hash=normalized_hash,
        extractor=extractor,
        marks=normalized.marks,
    )

    if require_articles:
        chunks = parse_law_text(normalized.vigente)
        empty_msg = f"Nenhum artigo encontrado em {law_number}"
    else:
        chunks = parse_extra_text(normalized.vigente)
        empty_msg = f"Nenhum conteúdo encontrado em {law_number}"

    if not chunks:
        doc, _ = await persist_legal_document(
            db,
            chunks=[],
            law_number=law_number,
            law_title=law_title,
            source_url=source_url,
            version=version,
            content_hash=source_hash,
            origin=origin,
            collected_at=collected,
            ingest_status="failed",
            last_error=empty_msg,
            manifest=manifest,
        )
        return IngestResult(
            success=False,
            published=False,
            message=empty_msg,
            document=doc,
            manifest=manifest,
        )

    doc, unchanged = await persist_legal_document(
        db,
        chunks=chunks,
        law_number=law_number,
        law_title=law_title,
        source_url=source_url,
        version=version,
        content_hash=source_hash,
        origin=origin,
        collected_at=collected,
        ingest_status="published",
        last_error=None,
        manifest=manifest,
    )
    if not unchanged:
        await build_fts_index(db)
    return IngestResult(
        success=True,
        unchanged=unchanged,
        published=True,
        document=doc,
        manifest=manifest,
    )
