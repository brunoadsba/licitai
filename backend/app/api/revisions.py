"""
Endpoints para Histórico e Versionamento de Edições de Documentos.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.document import Document, DocumentItem
from app.models.document_revision import DocumentRevision
from app.schemas.document import (
    DocumentRevisionCreate,
    DocumentRevisionListResponse,
    DocumentRevisionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents/{document_id}/revisions", tags=["Revisões de Documento"])


def _snapshot_items(items: list[DocumentItem]) -> list[dict]:
    return [
        {
            "item_number": i.item_number,
            "title": i.title or "",
            "content": i.content or "",
            "page_number": i.page_number,
            "item_order": i.item_order,
            "item_type": i.item_type,
        }
        for i in sorted(
            (x for x in items if getattr(x, "archived_at", None) is None),
            key=lambda x: x.item_order,
        )
    ]


@router.post(
    "",
    response_model=DocumentRevisionResponse,
    status_code=201,
    summary="Salvar snapshot de versão",
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
        .with_for_update()
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    max_v = await db.execute(
        select(func.coalesce(func.max(DocumentRevision.versao), 0)).where(
            DocumentRevision.document_id == document_id
        )
    )
    proxima_versao = (max_v.scalar() or 0) + 1

    revision = DocumentRevision(
        document_id=document_id,
        versao=proxima_versao,
        rotulo=data.rotulo,
        descricao=data.descricao,
        items_snapshot=_snapshot_items(doc.items),
    )

    db.add(revision)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "Conflito ao gerar a versão do snapshot "
                "(outra criação simultânea venceu). Tente novamente."
            ),
        ) from exc
    await db.refresh(revision)
    return DocumentRevisionResponse.model_validate(revision)


@router.get(
    "",
    response_model=DocumentRevisionListResponse,
    summary="Listar histórico de versões",
)
async def list_revisions(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
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
)
async def get_revision(
    document_id: uuid.UUID,
    versao: int,
    db: AsyncSession = Depends(get_db),
):
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
    description=(
        "Restaura criando NOVO conjunto de itens e arquivando os atuais "
        "(não apaga correções via cascade)."
    ),
)
async def restore_revision(
    document_id: uuid.UUID,
    versao: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Restore seguro:
    1. Snapshot do estado atual como nova revisão (backup).
    2. Arquiva itens ativos (archived_at) — correções permanecem.
    3. Cria novo conjunto de DocumentItem a partir do snapshot.
    """
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
        .with_for_update()
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    max_v = await db.execute(
        select(func.coalesce(func.max(DocumentRevision.versao), 0)).where(
            DocumentRevision.document_id == document_id
        )
    )
    backup_versao = (max_v.scalar() or 0) + 1
    db.add(
        DocumentRevision(
            document_id=document_id,
            versao=backup_versao,
            rotulo=f"Backup automático (pré-restauro v{versao})",
            descricao=(
                f"Estado do documento capturado antes de restaurar a versão {versao} "
                f"('{revision.rotulo}')."
            ),
            items_snapshot=_snapshot_items(doc.items),
        )
    )

    now = datetime.now(timezone.utc)
    active_items = [i for i in doc.items if getattr(i, "archived_at", None) is None]
    for item in active_items:
        item.archived_at = now

    new_item_ids: list[str] = []
    for data in sorted(revision.items_snapshot, key=lambda d: d.get("item_order", 0)):
        new_item = DocumentItem(
            document_id=document_id,
            item_number=data["item_number"],
            title=data.get("title") or "",
            content=data["content"],
            page_number=data.get("page_number"),
            item_order=data.get("item_order", 0),
            item_type=data.get("item_type", "item"),
        )
        db.add(new_item)
        await db.flush()
        new_item_ids.append(str(new_item.id))

    doc.total_items = len(revision.items_snapshot)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflito ao restaurar versão. Tente novamente.",
        ) from exc

    return {
        "message": (
            f"Documento restaurado para a versão {versao} ('{revision.rotulo}'). "
            f"Itens anteriores arquivados (correções preservadas). "
            f"Estado anterior salvo como versão {backup_versao}."
        ),
        "document_id": str(document_id),
        "versao_restaurada": versao,
        "versao_backup": backup_versao,
        "new_item_ids": new_item_ids,
    }
