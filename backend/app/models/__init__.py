"""Pacote de modelos SQLAlchemy."""

from app.models.document import Document, DocumentItem
from app.models.document_revision import DocumentRevision
from app.models.analysis import Analysis, Correction
from app.models.legal import LegalDocument, LegalChunk
from app.models.comparison import (
    Fornecedor,
    Molde,
    Comparacao,
    ComparacaoResultado,
)
from app.models.chat import ChatConversation, ChatMessage

__all__ = [
    "Document",
    "DocumentItem",
    "DocumentRevision",
    "Analysis",
    "Correction",
    "LegalDocument",
    "LegalChunk",
    "Fornecedor",
    "Molde",
    "Comparacao",
    "ComparacaoResultado",
    "ChatConversation",
    "ChatMessage",
]
