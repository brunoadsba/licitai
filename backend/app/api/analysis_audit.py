"""Pacote de auditoria jurídica (Fase 8)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.models.retrieval import RetrievalRun

router = APIRouter(prefix="/analysis", tags=["Análise"])


class AuditCorrection(BaseModel):
    id: uuid.UUID
    item_number: str | None
    de: str
    para: str
    justification: str
    legal_basis: str | None
    corpus_version: str | None
    retrieval_run_id: str | None
    review_status: str
    review_note: str | None
    reviewed_at: str | None
    grounded: bool | None


class AuditPackResponse(BaseModel):
    analysis_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    analyzed_at: str | None
    corpus_version: str | None
    final_opinion: str | None
    corrections: list[AuditCorrection]
    retrieval_runs: list[dict]


@router.get("/{analysis_id}/audit-pack", response_model=AuditPackResponse)
async def get_audit_pack(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Analysis)
        .options(
            selectinload(Analysis.corrections),
            selectinload(Analysis.document).selectinload(Document.items),
        )
        .where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    items = {str(i.id): i for i in (analysis.document.items or [])}
    snapshot = analysis.run_snapshot or {}
    rows: list[AuditCorrection] = []
    for c in analysis.corrections:
        ev = c.evidence or {}
        item = items.get(str(c.document_item_id))
        rows.append(
            AuditCorrection(
                id=c.id,
                item_number=getattr(item, "item_number", None) or ev.get("item_number"),
                de=ev.get("de") or c.original_text,
                para=ev.get("para") or c.suggested_text,
                justification=c.justification,
                legal_basis=c.legal_basis,
                corpus_version=ev.get("corpus_version"),
                retrieval_run_id=ev.get("retrieval_run_id"),
                review_status=c.review_status,
                review_note=c.review_note,
                reviewed_at=c.reviewed_at.isoformat() if c.reviewed_at else None,
                grounded=ev.get("grounded"),
            )
        )

    run_ids = [uuid.UUID(str(x)) for x in (snapshot.get("retrieval_run_ids") or []) if x]
    runs = []
    if run_ids:
        found = (
            await db.execute(select(RetrievalRun).where(RetrievalRun.id.in_(run_ids)))
        ).scalars().all()
        runs = [
            {
                "id": str(r.id),
                "corpus_version": r.corpus_version,
                "retrieved_ids": r.retrieved_ids,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in found
        ]

    return AuditPackResponse(
        analysis_id=analysis.id,
        document_id=analysis.document_id,
        document_name=analysis.document.filename_original,
        analyzed_at=analysis.completed_at.isoformat() if analysis.completed_at else None,
        corpus_version=snapshot.get("corpus_version"),
        final_opinion=analysis.final_opinion,
        corrections=rows,
        retrieval_runs=runs,
    )
