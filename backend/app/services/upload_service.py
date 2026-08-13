"""
Pipeline de upload de documentos: validação, persistência e parsing.

Extraído de app/api/documents.py para manter os endpoints enxutos e
permitir reuso (ex.: scripts de importação em lote).
"""

import logging

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentItem
from app.services.parser import parse_document
from app.utils.file_validation import (
    UPLOAD_DIR,
    generate_safe_filename,
    get_upload_path,
    validate_file_content,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)


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


async def parse_e_inserir_itens(
    db: AsyncSession, document: Document, file_ext: str
) -> bool:
    """Parseia o documento e insere os itens; False em caso de erro de parsing."""
    file_path = get_upload_path(document.filename_stored)
    try:
        items = await parse_document(file_path, file_ext)
    except Exception:
        logger.exception("Erro ao parsear documento %s", document.id)
        document.status = "error"
        document.error_message = "Erro ao processar o documento. Verifique o formato."
        await db.flush()
        return False

    for order, item_data in enumerate(items):
        db.add(DocumentItem(
            document_id=document.id,
            item_number=item_data["item_number"],
            title=item_data.get("title"),
            content=item_data["content"],
            page_number=item_data.get("page_number"),
            item_order=order,
            item_type=item_data.get("item_type", "item"),
        ))

    document.total_items = len(items)
    document.status = "parsed"
    await db.flush()
    return True
