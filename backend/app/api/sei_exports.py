"""Exports SEI/HTML/DOCX — extraído de `api/analysis.py`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis_filters import _filter_corrections
from app.database import get_db
from app.models.analysis import Analysis, Correction
from app.models.document import Document
from app.schemas.analysis import (
    CorrectedHtmlResponse,
    CorrectedHtmlSkip,
    CorrectionResponse,
    SeiPackEntry,
    SeiPackResponse,
)
from app.services.analyzer.corrected_document import (
    build_corrected_docx,
    build_corrected_html,
    build_sei_pack_text,
)

router = APIRouter(prefix="/analysis", tags=["Análise"])


@router.get(
    "/{analysis_id}/sei-pack",
    response_model=SeiPackResponse,
    summary="Pacote SEI ordenado",
    description=(
        "Texto consolidado com correções aprovadas/ajustadas, ordenadas por item, "
        "para colar no SEI."
    ),
)
async def get_sei_pack(
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

    items_by_id = {item.id: item for item in (analysis.document.items or [])}
    filtered = _filter_corrections(analysis.corrections, for_sei=True)

    def sort_key(c: Correction):
        item = items_by_id.get(c.document_item_id)
        order = (getattr(item, "item_order", 0) or 0) if item else 0
        number = (getattr(item, "item_number", "") or "") if item else ""
        return (order, number, str(c.id))

    entries: list[SeiPackEntry] = []
    entry_dicts: list[dict] = []
    for c in sorted(filtered, key=sort_key):
        item = items_by_id.get(c.document_item_id)
        item_number = getattr(item, "item_number", "?") if item else "?"
        title = getattr(item, "title", None) if item else None
        entry = SeiPackEntry(
            correction_id=c.id,
            item_number=str(item_number),
            title=title,
            suggested_text=c.suggested_text,
            justification=c.justification or "",
            legal_basis=c.legal_basis,
            severity=c.severity,
            category=c.category,
        )
        entries.append(entry)
        entry_dicts.append(entry.model_dump())

    text = build_sei_pack_text(
        document_name=analysis.document.filename_original,
        entries=entry_dicts,
    )
    return SeiPackResponse(
        analysis_id=analysis.id,
        document_id=analysis.document_id,
        document_name=analysis.document.filename_original,
        total=len(entries),
        text=text,
        entries=entries,
    )


@router.get(
    "/{analysis_id}/corrected-html",
    response_model=CorrectedHtmlResponse,
    summary="TR HTML corrigido",
    description=(
        "Documento completo em HTML com replaces DE→PARA das correções "
        "aprovadas/ajustadas."
    ),
)
async def get_corrected_html(
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

    if analysis.status not in ("completed", "completed_with_errors"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise concluir antes de exportar o TR corrigido.",
        )

    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma correção aprovada ou ajustada para montar o TR corrigido.",
        )

    by_item: dict = {}
    for c in filtered:
        by_item.setdefault(c.document_item_id, []).append(c)

    html_doc, applied, skipped = build_corrected_html(
        filename=analysis.document.filename_original,
        items=list(analysis.document.items or []),
        corrections_by_item=by_item,
    )
    return CorrectedHtmlResponse(
        document_id=analysis.document_id,
        analysis_id=analysis.id,
        document_name=analysis.document.filename_original,
        applied_corrections=len(applied),
        skipped_corrections=[
            CorrectedHtmlSkip(
                correction_id=s["correction_id"],
                reason=s["reason"],
            )
            for s in skipped
            if s.get("correction_id") is not None
        ],
        html=html_doc,
    )


@router.get(
    "/{analysis_id}/corrected-docx",
    summary="TR DOCX corrigido",
    description=(
        "Download .docx com replaces DE→PARA das correções aprovadas/ajustadas."
    ),
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        }
    },
)
async def get_corrected_docx(
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

    if analysis.status not in ("completed", "completed_with_errors"):
        raise HTTPException(
            status_code=409,
            detail="Aguarde a análise concluir antes de exportar o TR corrigido.",
        )

    filtered = _filter_corrections(analysis.corrections, for_sei=True)
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma correção aprovada ou ajustada para montar o TR corrigido.",
        )

    by_item: dict = {}
    for c in filtered:
        by_item.setdefault(c.document_item_id, []).append(c)

    payload, _applied, _skipped = build_corrected_docx(
        filename=analysis.document.filename_original,
        items=list(analysis.document.items or []),
        corrections_by_item=by_item,
    )
    safe_name = "".join(
        ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
        for ch in (analysis.document.filename_original or "tr")
    )
    if not safe_name.lower().endswith(".docx"):
        safe_name = f"{safe_name}.docx"
    return Response(
        content=payload,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Applied-Corrections": str(len(_applied)),
            "X-Skipped-Corrections": str(len(_skipped)),
        },
    )
