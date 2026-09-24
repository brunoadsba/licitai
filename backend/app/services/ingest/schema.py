"""Contratos da ingestão jurídica (Fase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.legal import LegalDocument
from app.services.parser.schema import LegalMark

IngestStatus = Literal["draft", "published", "failed"]


class IngestManifest(BaseModel):
    origin: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None
    source_hash: str
    normalized_hash: str
    extractor: str = "text"
    stages: list[str] = Field(
        default_factory=lambda: [
            "source",
            "extract",
            "normalize",
            "validate",
            "version",
            "index",
        ]
    )
    marks: list[LegalMark] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IngestResult(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    success: bool
    unchanged: bool = False
    published: bool = False
    message: str | None = None
    document: LegalDocument | None = None
    manifest: IngestManifest | None = None
