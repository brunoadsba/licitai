"""Pacote de modelos SQLAlchemy."""

from app.models.document import Document, DocumentItem
from app.models.analysis import Analysis, Correction
from app.models.legal import LegalDocument, LegalChunk
from app.models.comparison import (
    Fornecedor,
    Molde,
    Comparacao,
    ComparacaoResultado,
)

__all__ = [
    "Document",
    "DocumentItem",
    "Analysis",
    "Correction",
    "LegalDocument",
    "LegalChunk",
    "Fornecedor",
    "Molde",
    "Comparacao",
    "ComparacaoResultado",
]
