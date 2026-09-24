"""Consulta de dispositivos: vigente por padrão; histórico só se pedido."""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_versioned import LegalProvision, LegalVersion, LegalWork


async def list_provisions(
    db: AsyncSession,
    *,
    law_number: str | None = None,
    path: str | None = None,
    article: str | None = None,
    at: date | None = None,
    include_historical: bool = False,
) -> list[LegalProvision]:
    stmt = (
        select(LegalProvision)
        .join(LegalVersion, LegalVersion.id == LegalProvision.version_id)
        .join(LegalWork, LegalWork.id == LegalProvision.work_id)
    )
    if law_number:
        stmt = stmt.where(LegalWork.law_number == law_number)
    if path:
        stmt = stmt.where(LegalProvision.path == path)
    if article:
        stmt = stmt.where(LegalProvision.article == article)
    if include_historical:
        stmt = stmt.where(LegalVersion.status.in_(("published", "superseded")))
    else:
        stmt = stmt.where(LegalVersion.status == "published")
        stmt = stmt.where(LegalProvision.status == "vigente")
    if at is not None:
        stmt = stmt.where(
            or_(LegalVersion.validity_start.is_(None), LegalVersion.validity_start <= at)
        )
        stmt = stmt.where(
            or_(LegalVersion.validity_end.is_(None), LegalVersion.validity_end >= at)
        )
    stmt = stmt.order_by(LegalProvision.path)
    return list((await db.execute(stmt)).scalars().all())


async def ancestors_and_related(
    db: AsyncSession, provision: LegalProvision
) -> list[LegalProvision]:
    """Caput e ancestrais do dispositivo, na ordem da raiz até o próprio."""
    chain: list[LegalProvision] = []
    current: LegalProvision | None = provision
    seen: set = set()
    while current and current.id not in seen:
        chain.append(current)
        seen.add(current.id)
        if current.parent_id is None:
            break
        current = (
            await db.execute(
                select(LegalProvision).where(LegalProvision.id == current.parent_id)
            )
        ).scalar_one_or_none()
    chain.reverse()
    return chain
