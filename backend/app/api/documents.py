"""
Endpoints para upload e gerenciamento de documentos.

Segurança:
- Validação de extensão (allowlist)
- Validação de conteúdo (magic bytes)
- Limite de tamanho
- Renomeação para UUID
- Armazenamento fora do web root
"""

import logging
import uuid

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.document import Document, DocumentItem
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentItemResponse,
)
from app.utils.file_validation import (
    validate_file_extension,
    validate_file_content,
    validate_file_size,
    generate_safe_filename,
    get_upload_path,
    UPLOAD_DIR,
)
from app.services.parser import parse_document


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documentos"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload de documento",
    description="Envia um PDF ou DOCX para análise. O documento será parseado automaticamente.",
)
async def upload_document(
    file: UploadFile = File(..., description="Arquivo PDF ou DOCX"),
    db: AsyncSession = Depends(get_db),
):
    """Upload seguro de documento com validação completa."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo é obrigatório.")

    # 1. Validar extensão (allowlist)
    try:
        file_ext = validate_file_extension(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Ler conteúdo do arquivo
    file_bytes = await file.read()

    # 3. Validar tamanho
    try:
        validate_file_size(len(file_bytes))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 4. Validar conteúdo real (magic bytes)
    try:
        validate_file_content(file_bytes, file_ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 5. Gerar nome seguro (UUID)
    safe_filename = generate_safe_filename(file_ext)
    file_path = get_upload_path(safe_filename)

    # 6. Salvar arquivo
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)
    except OSError:
        logger.exception("Erro ao salvar arquivo")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao salvar o arquivo.",
        )

    # 7. Criar registro no banco
    document = Document(
        filename_original=file.filename,
        filename_stored=safe_filename,
        file_type=file_ext,
        file_size_bytes=len(file_bytes),
        status="uploaded",
    )
    db.add(document)
    await db.flush()

    # 8. Parsear documento automaticamente
    try:
        document.status = "parsing"
        await db.flush()

        items = await parse_document(file_path, file_ext)

        for order, item_data in enumerate(items):
            db_item = DocumentItem(
                document_id=document.id,
                item_number=item_data["item_number"],
                title=item_data.get("title"),
                content=item_data["content"],
                page_number=item_data.get("page_number"),
                item_order=order,
                item_type=item_data.get("item_type", "item"),
            )
            db.add(db_item)

        document.total_items = len(items)
        document.status = "parsed"

    except Exception:
        logger.exception("Erro ao parsear documento %s", document.id)
        document.status = "error"
        document.error_message = "Erro ao processar o documento. Verifique o formato."

    await db.flush()

    return DocumentResponse.model_validate(document)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="Listar documentos",
    description="Retorna todos os documentos enviados, ordenados por data.",
)
async def list_documents(
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os documentos."""
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Detalhes do documento",
    description="Retorna os detalhes completos de um documento com seus itens estruturados.",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retorna documento com itens."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # Contar correções por item
    items_response = []
    for item in document.items:
        item_dict = DocumentItemResponse.model_validate(item)
        # Correções serão contadas quando houver análise
        items_response.append(item_dict)

    response = DocumentDetailResponse.model_validate(document)
    response.items = items_response

    return response


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Remover documento",
    description="Remove um documento e seu arquivo do sistema.",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove documento e arquivo físico."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # Remover arquivo físico
    try:
        file_path = get_upload_path(document.filename_stored)
        if file_path.exists():
            file_path.unlink()
    except (ValueError, OSError):
        logger.warning("Não foi possível remover arquivo: %s", document.filename_stored)

    # Remover do banco (cascade remove itens e análises)
    await db.delete(document)
