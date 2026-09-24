"""
Pipeline de upload: validação, persistência e enfileiramento do parse.
"""

import logging

import aiofiles
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentItem
from app.models.job import Job
from app.services.jobs import enqueue
from app.services.parser import ParseResult, parse_document
from app.utils.file_validation import (
    UPLOAD_DIR,
    generate_safe_filename,
    get_upload_path,
    validate_file_content,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)

_PARSE_ACTIVE = ("pending", "running")


class UploadValidationError(ValueError):
    """Falha de validação de upload que deve virar HTTP 400."""


def validar_upload(filename: str, file_bytes: bytes) -> str:
    """Valida nome, extensão, tamanho e conteúdo real; devolve a extensão."""
    if not filename:
        raise UploadValidationError("Nome do arquivo é obrigatório.")

    try:
        file_ext = validate_file_extension(filename)
        validate_file_size(len(file_bytes))
        validate_file_content(file_bytes, file_ext)
    except ValueError as e:
        raise UploadValidationError(str(e)) from e

    return file_ext


async def salvar_arquivo_upload(file_bytes: bytes, file_ext: str) -> str:
    """Persiste o arquivo com nome UUID seguro; devolve o nome armazenado."""
    safe_filename = generate_safe_filename(file_ext)
    file_path = get_upload_path(safe_filename)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    return safe_filename


async def enqueue_document_parse(db: AsyncSession, document: Document) -> Job:
    """Enfileira parse no worker. Não executa extração pesada no request."""
    doc_id = str(document.id)
    result = await db.execute(
        select(Job).where(Job.type == "parse", Job.status.in_(_PARSE_ACTIVE))
    )
    for job in result.scalars():
        if (job.payload or {}).get("document_id") == doc_id:
            return job
    return await enqueue(db, "parse", {"document_id": doc_id})


async def parse_e_inserir_itens(
    db: AsyncSession, document: Document, file_ext: str
) -> bool:
    """Parseia no worker e insere itens a partir da estrutura intermediária."""
    file_path = get_upload_path(document.filename_stored)
    try:
        parsed = await parse_document(file_path, file_ext)
    except Exception:
        logger.exception("Erro ao parsear documento %s", document.id)
        document.status = "error"
        document.error_message = "Erro ao processar o documento. Verifique o formato."
        await db.flush()
        return False

    if not isinstance(parsed, ParseResult):
        parsed = ParseResult.model_validate(parsed)
    if not parsed.items:
        document.status = "error"
        document.error_message = "Documento incompleto: nenhum item extraído."
        await db.flush()
        return False

    await db.execute(
        delete(DocumentItem).where(DocumentItem.document_id == document.id)
    )
    for order, item in enumerate(parsed.items):
        db.add(
            DocumentItem(
                document_id=document.id,
                item_number=item.item_number,
                title=item.title,
                content=item.content,
                page_number=item.page_number,
                item_order=order,
                item_type=item.item_type,
            )
        )

    document.total_items = len(parsed.items)
    document.status = "parsed"
    document.error_message = None
    await db.flush()
    return True
