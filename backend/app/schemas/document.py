"""
Schemas Pydantic para documentos — validação de entrada e saída.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    total_items: int
    status: str
    created_at: datetime
    updated_at: datetime


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
    total_items: int
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[DocumentItemResponse] = []
