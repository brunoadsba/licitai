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

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.analysis import estimate_tokens
from app.config import settings
from app.database import get_db
from app.models.analysis import Analysis
from app.models.document import Document
from app.schemas.document import (
    DiffItemResponse,
    DiffRequest,
    DiffResponse,
    DocumentDetailResponse,
    DocumentItemResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.comparator.diff import diff_terms, resumir_diffs
from app.services.upload_service import (
    UploadValidationError,
    parse_e_inserir_itens,
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
    description="Envia um PDF ou DOCX para análise. O documento será parseado automaticamente.",
)
async def upload_document(
    file: UploadFile = File(..., description="Arquivo PDF ou DOCX"),
    document_type: str = Form(default="tr", description="Tipo: 'tr' ou 'proposta'"),
    fornecedor_id: uuid.UUID | None = Form(
        default=None, description="Fornecedor vinculado (obrigatório p/ proposta)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Upload seguro de documento com validação completa."""

    if document_type not in TIPOS_DOCUMENTO:
        raise HTTPException(
            status_code=400,
            detail=f"document_type inválido. Use um de: {sorted(TIPOS_DOCUMENTO)}",
        )

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

    file_bytes = await file.read()

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
        status="uploaded",
    )
    db.add(document)
    await db.flush()

    document.status = "parsing"
    await parse_e_inserir_itens(db, document, file_ext)

    # Commit explícito antes do 201: evita corrida com DELETE/GET imediatos
    # (o commit pós-resposta do get_db chega depois que o cliente já recebeu 201).
    await db.commit()

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
        items_response.append(DocumentItemResponse.model_validate(item))

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

    try:
        file_path = get_upload_path(document.filename_stored)
        if file_path.exists():
            file_path.unlink()
    except (ValueError, OSError):
        logger.warning("Não foi possível remover arquivo: %s", document.filename_stored)

    await db.delete(document)
    # Commit explícito: o commit do get_db ocorre após o envio da resposta
    await db.commit()
