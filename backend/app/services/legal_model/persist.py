"""Persistência de works/versions/provisions. Versões publicadas são imutáveis."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_versioned import LegalProvision, LegalVersion, LegalWork
from app.services.legal_model.catalog import classify_work, may_publish_work
from app.services.legal_model.provisions import ProvisionDraft, parse_provisions


async def upsert_versioned_work(
    db: AsyncSession,
    *,
    content: str,
    law_number: str,
    law_title: str,
    source_url: str | None,
    collected_at: datetime | None,
    content_hash: str,
    source_version: str | None = None,
    validation_source: str | None = None,
) -> LegalVersion | None:
    """Cria work + versão. Hash igual reusa a versão; hash novo supersede."""
    drafts = parse_provisions(content)
    if not drafts:
        return None

    work = await _get_or_create_work(db, law_number, law_title)
    existing = await _latest_version(db, work.id)
    if existing and existing.content_hash == content_hash:
        return existing

    if existing and existing.status == "published":
        existing.status = "superseded"
        await _mark_provisions_historical(db, existing.id)
        await db.flush()

    publish = may_publish_work(law_number, source_version)
    version = LegalVersion(
        work_id=work.id,
        source_url=source_url,
        collected_at=collected_at,
        content_hash=content_hash,
        wording="consolidada",
        status="published" if publish else "unpublished",
        validation_source=validation_source,
    )
    db.add(version)
    await db.flush()
    await _insert_provisions(db, work.id, version.id, drafts, published=publish)
    await db.flush()
    return version


async def _get_or_create_work(
    db: AsyncSession, law_number: str, law_title: str
) -> LegalWork:
    result = await db.execute(
        select(LegalWork).where(LegalWork.law_number == law_number)
    )
    work = result.scalar_one_or_none()
    if work:
        return work
    meta = classify_work(law_number, law_title)
    work = LegalWork(
        law_number=law_number,
        title=law_title,
        kind=meta.get("kind") or "lei",
        issuing_body=meta.get("issuing_body"),
        sphere=meta.get("sphere"),
        jurisdiction=meta.get("jurisdiction"),
        subject_area=meta.get("subject_area"),
    )
    db.add(work)
    await db.flush()
    return work


async def _latest_version(
    db: AsyncSession, work_id
) -> LegalVersion | None:
    result = await db.execute(
        select(LegalVersion)
        .where(LegalVersion.work_id == work_id)
        .order_by(LegalVersion.created_at.desc())
    )
    return result.scalars().first()


async def _mark_provisions_historical(db: AsyncSession, version_id) -> None:
    result = await db.execute(
        select(LegalProvision).where(LegalProvision.version_id == version_id)
    )
    for provision in result.scalars():
        if provision.status == "vigente":
            provision.status = "historical"


async def _insert_provisions(
    db: AsyncSession,
    work_id,
    version_id,
    drafts: list[ProvisionDraft],
    *,
    published: bool,
) -> dict[str, LegalProvision]:
    by_path: dict[str, LegalProvision] = {}
    for draft in drafts:
        status = draft.status if published else "historical"
        row = LegalProvision(
            version_id=version_id,
            work_id=work_id,
            path=draft.path,
            article=draft.article,
            paragraph=draft.paragraph,
            inciso=draft.inciso,
            alinea=draft.alinea,
            item=draft.item,
            canonical_text=draft.canonical_text,
            status=status,
            provision_hash=draft.provision_hash,
        )
        db.add(row)
        by_path[draft.path] = row
    await db.flush()
    for draft in drafts:
        if draft.parent_path and draft.parent_path in by_path:
            by_path[draft.path].parent_id = by_path[draft.parent_path].id
    return by_path
