"""Pacote RAG (Retrieval-Augmented Generation)."""

from app.services.rag.loader import build_fts_index, ingest_law_text, parse_law_text
from app.services.rag.retriever import RetrievedChunk, retrieve

__all__ = [
    "ingest_law_text",
    "build_fts_index",
    "parse_law_text",
    "retrieve",
    "RetrievedChunk",
]
