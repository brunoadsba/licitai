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

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis_scoring import estimate_tokens
from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentItemResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.privacy import (
    CloudPrivacyError,
    assert_cloud_allowed_for_document,
    resolve_classification,
)
from app.services.upload_service import (
    UploadValidationError,
    enqueue_document_parse,
    salvar_arquivo_upload,
    validar_upload,
)
from app.utils.file_validation import get_upload_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documentos"])

TIPOS_DOCUMENTO = {"tr", "proposta"}


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload de documento",
    description="Envia um PDF ou DOCX. O parse pesado corre no worker; a resposta não espera a extração.",
)
async def upload_document(
    file: UploadFile = File(..., description="Arquivo PDF ou DOCX"),
    document_type: str = Form(default="tr", description="Tipo: 'tr' ou 'proposta'"),
    fornecedor_id: uuid.UUID | None = Form(
        default=None, description="Fornecedor vinculado (obrigatório p/ proposta)"
    ),
    classification: str | None = Form(
        default=None,
        description="Classificação de confidencialidade (ex.: sigiloso)",
    ),
    x_document_classification: str | None = Header(
        default=None, alias="X-Document-Classification"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Upload seguro de documento com validação completa."""

    if document_type not in TIPOS_DOCUMENTO:
        raise HTTPException(
            status_code=400,
            detail=f"document_type inválido. Use um de: {sorted(TIPOS_DOCUMENTO)}",
        )

    resolved_classification = resolve_classification(
        form_value=classification,
        header_value=x_document_classification,
    )
    try:
        assert_cloud_allowed_for_document(resolved_classification)
    except CloudPrivacyError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    # Pré-checagem além do validar_upload: rejeita antes de alocar o corpo em memória.
    if file.size is not None and file.size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Arquivo muito grande: "
                f"{round(file.size / (1024 * 1024), 2)}MB. "
                f"Limite máximo: {settings.max_upload_size_mb}MB."
            ),
        )

    file_bytes = await file.read(settings.max_upload_size_bytes + 1)
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Arquivo muito grande: "
                f"{round(len(file_bytes) / (1024 * 1024), 2)}MB. "
                f"Limite máximo: {settings.max_upload_size_mb}MB."
            ),
        )

    try:
        file_ext = validar_upload(file.filename, file_bytes)
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if document_type == "proposta" and fornecedor_id is None:
        raise HTTPException(
            status_code=400,
            detail="Propostas precisam de fornecedor_id.",
        )

    if document_type == "tr":
        fornecedor_id = None

    try:
        safe_filename = await salvar_arquivo_upload(file_bytes, file_ext)
    except OSError as e:
        logger.exception("Erro ao salvar arquivo")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao salvar o arquivo.",
        ) from e

    document = Document(
        filename_original=file.filename,
        filename_stored=safe_filename,
        file_type=file_ext,
        file_size_bytes=len(file_bytes),
        document_type=document_type,
        fornecedor_id=fornecedor_id,
        classification=resolved_classification,
        status="uploaded",
    )
    db.add(document)

    try:
        await db.flush()
        await enqueue_document_parse(db, document)
        # Commit explícito antes do 201: o parse pesado corre no worker.
        await db.commit()
    except Exception:
        await db.rollback()
        # Compensação: arquivo já no disco sem linha no DB → remover.
        try:
            path = get_upload_path(safe_filename)
            if path.exists():
                path.unlink()
                logger.warning(
                    "upload.compensation removed orphan file=%s", safe_filename
                )
        except OSError:
            logger.exception(
                "upload.compensation failed to remove file=%s", safe_filename
            )
        raise

    return DocumentResponse.model_validate(document)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="Listar documentos",
    description="Retorna todos os documentos enviados, ordenados por data.",
)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lista documentos com paginação (backward compatible)."""
    total = (
        await db.execute(select(func.count()).select_from(Document))
    ).scalar_one()

    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    documents = result.scalars().all()

    responses = [DocumentResponse.model_validate(d) for d in documents]
    await _attach_token_estimates(db, responses)

    return DocumentListResponse(
        documents=responses,
        total=total,
    )


async def _attach_token_estimates(
    db: AsyncSession, responses: list[DocumentResponse]
) -> None:
    """Anexa a estimativa de tokens da análise mais recente concluída de cada documento."""
    doc_ids = [r.id for r in responses if r.status == "completed"]
    if not doc_ids:
        return

    result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.corrections))
        .where(Analysis.document_id.in_(doc_ids), Analysis.status == "completed")
        .order_by(Analysis.created_at.desc())
    )
    estimates: dict[uuid.UUID, int] = {}
    for analysis in result.scalars():
        if analysis.document_id is not None:
            estimates.setdefault(analysis.document_id, estimate_tokens(analysis))

    for resp in responses:
        resp.tokens_estimated = estimates.get(resp.id)


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

    items_response = []
    for item in document.items:
        if getattr(item, "archived_at", None) is not None:
            continue
        items_response.append(DocumentItemResponse.model_validate(item))

    response = DocumentDetailResponse.model_validate(document)
    response.items = items_response
    response.total_items = len(items_response)

    return response


@router.post(
    "/{document_id}/reparse",
    response_model=DocumentResponse,
    summary="Reprocessar parse",
    description="Enfileira novamente o parse de um documento com falha ou já extraído.",
)
async def reparse_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Reprocessa extração sem novo upload (falha reprocessável)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    document.status = "uploaded"
    document.error_message = None
    await enqueue_document_parse(db, document)
    await db.commit()
    return DocumentResponse.model_validate(document)


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

    try:
        file_path = get_upload_path(document.filename_stored)
        if file_path.exists():
            file_path.unlink()
    except (ValueError, OSError):
        logger.warning("Não foi possível remover arquivo: %s", document.filename_stored)

    await db.delete(document)
    # Commit explícito: o commit do get_db ocorre após o envio da resposta
    await db.commit()
