"""Pacote RAG (Retrieval-Augmented Generation)."""

from app.services.rag.loader import ingest_law_text, build_fts_index, parse_law_text
from app.services.rag.retriever import retrieve, RetrievedChunk

__all__ = [
    "ingest_law_text",
    "build_fts_index",
    "parse_law_text",
    "retrieve",
    "RetrievedChunk",
]
