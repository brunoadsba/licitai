"""
Schemas Pydantic para documentos — validação de entrada e saída.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator


def _ensure_tz(v: datetime) -> datetime:
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


AwareDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]


class DocumentCreate(BaseModel):
    """Schema para criação de documento (usado internamente após upload)."""
    filename_original: str = Field(..., max_length=500)
    filename_stored: str = Field(..., max_length=255)
    file_type: str = Field(..., pattern=r"^(pdf|docx|odt)$")
    file_size_bytes: int = Field(..., gt=0)


class DocumentItemResponse(BaseModel):
    """Schema de resposta para um item do documento."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_number: str
    title: str | None = None
    content: str
    page_number: int | None = None
    item_order: int
    item_type: str
    corrections_count: int = 0


class DocumentResponse(BaseModel):
    """Schema de resposta resumida de documento."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename_original: str
    file_type: str
    file_size_bytes: int
    document_type: str = "tr"
    fornecedor_id: uuid.UUID | None = None
    total_items: int
    status: str
    created_at: AwareDatetime
    updated_at: AwareDatetime


class DocumentListResponse(BaseModel):
    """Lista paginada de documentos."""
    documents: list[DocumentResponse]
    total: int


class DocumentDetailResponse(BaseModel):
    """Detalhes completos de um documento com seus itens."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename_original: str
    file_type: str
    file_size_bytes: int
    document_type: str = "tr"
    fornecedor_id: uuid.UUID | None = None
    total_items: int
    status: str
    error_message: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    items: list[DocumentItemResponse] = []


class DiffRequest(BaseModel):
    """Solicitação de diff entre duas versões de TR."""
    documento_antigo_id: uuid.UUID
    documento_novo_id: uuid.UUID


class DiffItemResponse(BaseModel):
    """Item do diff entre versões do TR."""
    status: str
    item_number: str
    titulo: str = ""
    conteudo_antes: str | None = None
    conteudo_depois: str | None = None


class DiffResponse(BaseModel):
    """Resultado do diff entre versões do TR."""
    documento_antigo_id: uuid.UUID
    documento_novo_id: uuid.UUID
    total: int
    resumo: dict[str, int]
    itens: list[DiffItemResponse]
