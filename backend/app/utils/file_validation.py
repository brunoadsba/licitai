"""
Validação segura de arquivos enviados pelo usuário.

Regras de segurança:
- Allowlist de extensões e MIME types
- Validação de magic bytes (conteúdo real do arquivo)
- Limite de tamanho
- Renomeação para UUID (nunca usa o nome original no filesystem)
- Path sanitization
"""

import logging
import os
import uuid
from pathlib import Path, PurePosixPath

import magic

from app.config import settings

logger = logging.getLogger(__name__)

# Diretório de uploads — configurável via env, padrão ./uploads.
# Criação física ocorre no lifespan do FastAPI e em salvar_arquivo_upload,
# nunca no import (evita side-effect em testes/read-only).
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()


def validate_file_extension(filename: str) -> str:
    """
    Valida a extensão do arquivo contra a allowlist.
    Retorna a extensão limpa (sem ponto, lowercase).

    Raises:
        ValueError: Se a extensão não é permitida.
    """
    # Usa apenas o basename para evitar path traversal
    safe_name = PurePosixPath(filename).name
    if not safe_name:
        raise ValueError("Nome de arquivo inválido.")

    _, ext = os.path.splitext(safe_name)
    ext_lower = ext.lower()

    if ext_lower not in settings.ALLOWED_FILE_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_FILE_EXTENSIONS))
        raise ValueError(
            f"Tipo de arquivo não permitido: '{ext_lower}'. "
            f"Tipos aceitos: {allowed}"
        )

    return ext_lower.lstrip(".")


def validate_file_content(file_bytes: bytes, expected_extension: str) -> str:
    """
    Valida o conteúdo real do arquivo via magic bytes.
    Previne que um arquivo malicioso seja disfarçado com extensão válida.

    Returns:
        MIME type detectado.

    Raises:
        ValueError: Se o conteúdo não corresponde ao tipo esperado.
    """
    detected_mime = magic.from_buffer(file_bytes[:8192], mime=True)

    # libmagic varia por host: DOCX/ODT (ZIP) podem vir como application/zip
    # ou octet-stream. Nesses casos, exige assinatura ZIP (PK..) e deixa o
    # parser validar a estrutura interna (falha segura se inválido).
    if expected_extension in ("docx", "odt") and detected_mime in (
        "application/zip",
        "application/x-zip-compressed",
        "application/octet-stream",
    ):
        if len(file_bytes) >= 4 and file_bytes[:4] == b"PK\x03\x04":
            return detected_mime
        raise ValueError(
            f"Conteúdo do arquivo não corresponde ao tipo esperado. "
            f"MIME detectado: {detected_mime}"
        )

    if detected_mime not in settings.ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Conteúdo do arquivo não corresponde ao tipo esperado. "
            f"MIME detectado: {detected_mime}"
        )

    # Verificar correspondência extensão ↔ MIME
    extension_mime_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "odt": "application/vnd.oasis.opendocument.text",
    }

    expected_mime = extension_mime_map.get(expected_extension)
    if expected_mime and detected_mime != expected_mime:
        raise ValueError(
            f"Extensão '{expected_extension}' não corresponde ao conteúdo "
            f"real do arquivo (MIME: {detected_mime})."
        )

    return detected_mime


def validate_file_size(size_bytes: int) -> None:
    """
    Valida o tamanho do arquivo contra o limite configurado.

    Raises:
        ValueError: Se o arquivo excede o limite.
    """
    if size_bytes > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_mb
        actual_mb = round(size_bytes / (1024 * 1024), 2)
        raise ValueError(
            f"Arquivo muito grande: {actual_mb}MB. "
            f"Limite máximo: {max_mb}MB."
        )

    if size_bytes == 0:
        raise ValueError("Arquivo vazio não é permitido.")


def generate_safe_filename(extension: str) -> str:
    """
    Gera um nome de arquivo seguro baseado em UUID.
    Nunca usa o nome original do arquivo.
    """
    return f"{uuid.uuid4().hex}.{extension}"


def get_upload_path(filename_stored: str) -> Path:
    """
    Retorna o caminho completo para o arquivo no diretório de uploads.
    Inclui verificação de path traversal.
    """
    safe_name = Path(filename_stored).name
    full_path = UPLOAD_DIR / safe_name

    resolved = full_path.resolve()
    upload_resolved = UPLOAD_DIR.resolve()

    try:
        is_inside = resolved.is_relative_to(upload_resolved)
    except AttributeError:
        is_inside = str(resolved).startswith(str(upload_resolved) + os.sep)
    if not is_inside or resolved == upload_resolved:
        logger.warning(
            "Tentativa de path traversal detectada: %s", filename_stored
        )
        raise ValueError("Caminho de arquivo inválido.")

    return full_path
