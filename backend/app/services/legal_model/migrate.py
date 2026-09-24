"""Migra amostra do modelo legado para works/versions/provisions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalChunk, LegalDocument
from app.models.legal_versioned import LegalIdMap, LegalProvision
from app.services.legal_model.persist import upsert_versioned_work


SAMPLE_LAWS = ("Lei 14.133/2021", "Lei 13.303/2016")


@dataclass
class MigrateReport:
    law_number: str
    old_chunks: int
    new_provisions: int
    mapped: int
    article_paths: list[str] = field(default_factory=list)
    missing_articles: list[str] = field(default_factory=list)


def _article_path(article: str | None) -> str | None:
    if not article:
        return None
    cleaned = article.replace("º", "").replace("°", "")
    match = re.search(r"(\d+[A-Za-z\-]+|\d+)", cleaned)
    if not match:
        return None
    return f"art.{match.group(1).lower()}"


async def migrate_sample(
    db: AsyncSession, law_numbers: tuple[str, ...] = SAMPLE_LAWS
) -> list[MigrateReport]:
    """Copia uma amostra. Não apaga legal_documents nem troca o índice."""
    reports: list[MigrateReport] = []
    for law_number in law_numbers:
        doc = (
            await db.execute(
                select(LegalDocument).where(LegalDocument.law_number == law_number)
            )
        ).scalar_one_or_none()
        if not doc:
            continue
        chunks = list(
            (
                await db.execute(
                    select(LegalChunk)
                    .where(LegalChunk.legal_document_id == doc.id)
                    .order_by(LegalChunk.chunk_index)
                )
            ).scalars().all()
        )
        content = "\n".join(chunk.chunk_text for chunk in chunks)
        version = await upsert_versioned_work(
            db,
            content=content,
            law_number=doc.law_number,
            law_title=doc.law_title,
            source_url=doc.source_url,
            collected_at=doc.collected_at,
            content_hash=doc.content_hash or "",
            source_version=doc.version,
            validation_source=doc.origin,
        )
        provisions = []
        if version:
            provisions = list(
                (
                    await db.execute(
                        select(LegalProvision).where(
                            LegalProvision.version_id == version.id
                        )
                    )
                ).scalars().all()
            )
        by_path = {p.path: p for p in provisions}
        mapped = 0
        missing: list[str] = []
        for chunk in chunks:
            path = _article_path(chunk.article)
            provision = by_path.get(path or "")
            if provision is None:
                missing.append(chunk.article or "")
                continue
            existing = (
                await db.execute(
                    select(LegalIdMap).where(LegalIdMap.old_chunk_id == chunk.id)
                )
            ).scalar_one_or_none()
            if not existing:
                db.add(
                    LegalIdMap(
                        old_chunk_id=chunk.id,
                        provision_id=provision.id,
                        legal_document_id=doc.id,
                    )
                )
            mapped += 1
        reports.append(
            MigrateReport(
                law_number=law_number,
                old_chunks=len(chunks),
                new_provisions=len(provisions),
                mapped=mapped,
                article_paths=[p.path for p in provisions if p.parent_id is None],
                missing_articles=[a for a in missing if a],
            )
        )
    await db.flush()
    return reports
