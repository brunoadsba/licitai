"""Pacote de modelos SQLAlchemy."""

from app.models.analysis import Analysis, Correction
from app.models.chat import ChatConversation, ChatMessage
from app.models.comparison import (
    Comparacao,
    ComparacaoResultado,
    Fornecedor,
    Molde,
)
from app.models.document import Document, DocumentItem
from app.models.document_revision import DocumentRevision
from app.models.job import Job
from app.models.legal import LegalChunk, LegalDocument

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
    "Job",
]
