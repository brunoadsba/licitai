"""
Endpoints para Histórico e Versionamento de Edições de Documentos.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.document import Document, DocumentItem
from app.models.document_revision import DocumentRevision
from app.schemas.document import (
    DocumentRevisionCreate,
    DocumentRevisionResponse,
    DocumentRevisionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents/{document_id}/revisions", tags=["Revisões de Documento"])


@router.post(
    "",
    response_model=DocumentRevisionResponse,
    status_code=201,
    summary="Salvar snapshot de versão",
    description="Cria uma nova versão historizada (snapshot) dos itens de um documento.",
)
async def create_revision(
    document_id: uuid.UUID,
    data: DocumentRevisionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um snapshot do documento atual com número de versão sequencial."""
    doc_result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # Descobrir próxima versão sequencial
    max_v = await db.execute(
        select(func.coalesce(func.max(DocumentRevision.versao), 0))
        .where(DocumentRevision.document_id == document_id)
    )
    proxima_versao = (max_v.scalar() or 0) + 1

    # Montar snapshot dos itens
    items_snapshot = [
        {
            "item_number": i.item_number,
            "title": i.title or "",
            "content": i.content or "",
            "page_number": i.page_number,
            "item_order": i.item_order,
            "item_type": i.item_type,
        }
        for i in sorted(doc.items, key=lambda x: x.item_order)
    ]

    revision = DocumentRevision(
        document_id=document_id,
        versao=proxima_versao,
        rotulo=data.rotulo,
        descricao=data.descricao,
        items_snapshot=items_snapshot,
    )

    db.add(revision)
    await db.commit()
    await db.refresh(revision)
    return DocumentRevisionResponse.model_validate(revision)


@router.get(
    "",
    response_model=DocumentRevisionListResponse,
    summary="Listar histórico de versões",
    description="Retorna todas as versões historizadas salvas para um documento.",
)
async def list_revisions(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna lista de revisões do documento ordenadas por versão decrescente."""
    result = await db.execute(
        select(DocumentRevision)
        .where(DocumentRevision.document_id == document_id)
        .order_by(DocumentRevision.versao.desc())
    )
    revisions = result.scalars().all()
    return DocumentRevisionListResponse(
        revisions=[DocumentRevisionResponse.model_validate(r) for r in revisions],
        total=len(revisions),
    )


@router.get(
    "/{versao}",
    response_model=DocumentRevisionResponse,
    summary="Obter versão específica",
    description="Retorna os detalhes e o snapshot completo de uma versão de documento.",
)
async def get_revision(
    document_id: uuid.UUID,
    versao: int,
    db: AsyncSession = Depends(get_db),
):
    """Retorna o snapshot de uma versão específica."""
    result = await db.execute(
        select(DocumentRevision).where(
            DocumentRevision.document_id == document_id,
            DocumentRevision.versao == versao,
        )
    )
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisão não encontrada.")
    return DocumentRevisionResponse.model_validate(revision)


@router.post(
    "/{versao}/restore",
    summary="Restaurar versão",
    description="Restaura os itens do documento ativo para o estado de um snapshot historizado.",
)
async def restore_revision(
    document_id: uuid.UUID,
    versao: int,
    db: AsyncSession = Depends(get_db),
):
    """Restaura o documento para o snapshot selecionado."""
    rev_result = await db.execute(
        select(DocumentRevision).where(
            DocumentRevision.document_id == document_id,
            DocumentRevision.versao == versao,
        )
    )
    revision = rev_result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisão não encontrada.")

    doc_result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # Atualizar itens existentes com os dados do snapshot
    snapshot_map = {item["item_number"]: item["content"] for item in revision.items_snapshot}

    for item in doc.items:
        if item.item_number in snapshot_map:
            item.content = snapshot_map[item.item_number]

    await db.commit()
    return {
        "message": f"Documento restaurado com sucesso para a versão {versao} ('{revision.rotulo}').",
        "document_id": document_id,
        "versao_restaurada": versao,
    }
