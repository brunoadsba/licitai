"""Consulta de dispositivos jurídicos versionados (Fase 8)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.legal_versioned import LegalProvision, LegalVersion, LegalWork
from app.services.legal_model.query import ancestors_and_related, list_provisions

router = APIRouter(prefix="/legal", tags=["Jurídico"])


class ProvisionResponse(BaseModel):
    id: uuid.UUID
    law_number: str
    law_title: str
    path: str
    article: str | None
    paragraph: str | None
    inciso: str | None
    alinea: str | None
    item: str | None
    canonical_text: str
    status: str
    version_status: str
    source_url: str | None
    validity_start: date | None
    validity_end: date | None
    ancestors: list[dict] = []


def _to_response(
    provision: LegalProvision,
    work: LegalWork,
    version: LegalVersion,
    ancestors: list[LegalProvision] | None = None,
) -> ProvisionResponse:
    return ProvisionResponse(
        id=provision.id,
        law_number=work.law_number,
        law_title=work.title,
        path=provision.path,
        article=provision.article,
        paragraph=provision.paragraph,
        inciso=provision.inciso,
        alinea=provision.alinea,
        item=provision.item,
        canonical_text=provision.canonical_text,
        status=provision.status,
        version_status=version.status,
        source_url=version.source_url,
        validity_start=version.validity_start,
        validity_end=version.validity_end,
        ancestors=[
            {"path": a.path, "text": a.canonical_text, "status": a.status}
            for a in (ancestors or [])
            if a.id != provision.id
        ],
    )


@router.get("/provisions", response_model=list[ProvisionResponse])
async def get_provisions(
    law_number: str | None = None,
    path: str | None = None,
    article: str | None = None,
    include_historical: bool = False,
    db: AsyncSession = Depends(get_db),
):
    rows = await list_provisions(
        db,
        law_number=law_number,
        path=path,
        article=article,
        include_historical=include_historical,
    )
    out: list[ProvisionResponse] = []
    for provision in rows[:40]:
        version = await db.get(LegalVersion, provision.version_id)
        work = await db.get(LegalWork, provision.work_id)
        if not version or not work:
            continue
        out.append(_to_response(provision, work, version))
    return out


@router.get("/provisions/{provision_id}", response_model=ProvisionResponse)
async def get_provision(
    provision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    provision = (
        await db.execute(
            select(LegalProvision)
            .options(selectinload(LegalProvision.version))
            .where(LegalProvision.id == provision_id)
        )
    ).scalar_one_or_none()
    if not provision:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")
    version = await db.get(LegalVersion, provision.version_id)
    work = await db.get(LegalWork, provision.work_id)
    if not version or not work:
        raise HTTPException(status_code=404, detail="Dispositivo sem versão.")
    chain = await ancestors_and_related(db, provision)
    return _to_response(provision, work, version, chain)
