"""Diff entre versões de TR — extraído de `api/documents.py`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.document import Document
from app.schemas.document import (
    DiffItemResponse,
    DiffRequest,
    DiffResponse,
)
from app.services.comparator.diff import diff_terms, resumir_diffs

router = APIRouter(prefix="/documents", tags=["Documentos"])


@router.post(
    "/diff",
    response_model=DiffResponse,
    summary="Comparar versões do TR",
    description=(
        "Compara dois documentos TR (antigo e novo) item a item, retornando "
        "itens inalterados, alterados, adicionados e removidos."
    ),
)
async def diff_documents(
    data: DiffRequest,
    db: AsyncSession = Depends(get_db),
):
    """Gera o diff entre duas versões de um Termo de Referência."""
    antigo = await _carregar_tr_items(db, data.documento_antigo_id)
    novo = await _carregar_tr_items(db, data.documento_novo_id)

    diffs = diff_terms(antigo, novo)

    return DiffResponse(
        documento_antigo_id=data.documento_antigo_id,
        documento_novo_id=data.documento_novo_id,
        total=len(diffs),
        resumo=resumir_diffs(diffs),
        itens=[
            DiffItemResponse.model_validate(d, from_attributes=True)
            for d in diffs
        ],
    )


async def _carregar_tr_items(
    db: AsyncSession, document_id: uuid.UUID
) -> list[dict]:
    """Carrega os itens de um documento TR, validando tipo e status."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    if document.document_type != "tr":
        raise HTTPException(
            status_code=400, detail="O documento informado não é um TR."
        )
    return [
        {
            "item_number": item.item_number,
            "title": item.title or "",
            "content": item.content or "",
        }
        for item in document.items
    ]
