"""Compara amostra legado × dispositivos. Não publica índice novo."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import LegalChunk, LegalDocument
from app.models.legal_versioned import LegalIdMap, LegalProvision, LegalWork
from app.services.legal_model.migrate import SAMPLE_LAWS, _article_path


@dataclass
class CompareReport:
    law_number: str
    chunk_articles: int
    provision_articles: int
    mapped: int
    unmapped_vigente: list[str]
    vetado_mapped: int
    hashes_filled: bool


async def compare_sample(
    db: AsyncSession, law_numbers: tuple[str, ...] = SAMPLE_LAWS
) -> list[CompareReport]:
    reports: list[CompareReport] = []
    for law_number in law_numbers:
        doc = (
            await db.execute(
                select(LegalDocument).where(LegalDocument.law_number == law_number)
            )
        ).scalar_one_or_none()
        work = (
            await db.execute(
                select(LegalWork).where(LegalWork.law_number == law_number)
            )
        ).scalar_one_or_none()
        if not doc or not work:
            continue
        chunks = list(
            (
                await db.execute(
                    select(LegalChunk).where(LegalChunk.legal_document_id == doc.id)
                )
            ).scalars().all()
        )
        provisions = list(
            (
                await db.execute(
                    select(LegalProvision).where(LegalProvision.work_id == work.id)
                )
            ).scalars().all()
        )
        maps = list(
            (
                await db.execute(
                    select(LegalIdMap).where(LegalIdMap.legal_document_id == doc.id)
                )
            ).scalars().all()
        )
        mapped_chunks = {row.old_chunk_id for row in maps}
        unmapped = []
        for chunk in chunks:
            if chunk.id in mapped_chunks:
                continue
            path = _article_path(chunk.article)
            if any(p.path == path and p.status == "vigente" for p in provisions):
                unmapped.append(chunk.article or "")
        vetado_mapped = 0
        by_id = {p.id: p for p in provisions}
        for row in maps:
            provision = by_id.get(row.provision_id)
            if provision and provision.status == "vetado":
                vetado_mapped += 1
        reports.append(
            CompareReport(
                law_number=law_number,
                chunk_articles=len(chunks),
                provision_articles=len({p.path for p in provisions if "/" not in p.path}),
                mapped=len(maps),
                unmapped_vigente=[a for a in unmapped if a],
                vetado_mapped=vetado_mapped,
                hashes_filled=bool(doc.content_hash),
            )
        )
    return reports
