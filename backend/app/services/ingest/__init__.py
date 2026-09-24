"""Ingestão jurídica idempotente (Fase 3)."""

from app.services.ingest.hashing import sha256_text
from app.services.ingest.pipeline import ingest_legal_source
from app.services.ingest.schema import IngestManifest, IngestResult

__all__ = [
    "ingest_legal_source",
    "sha256_text",
    "IngestManifest",
    "IngestResult",
]
