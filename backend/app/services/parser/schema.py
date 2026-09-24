"""Estrutura intermediária de parse — validável antes da persistência."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LegalMarkKind = Literal["strikethrough", "vetado", "redacao_dada"]
LegalMarkStatus = Literal["historical", "annotation"]


class LegalMark(BaseModel):
    """Marcação jurídica extraída (tachado, veto, redação posterior)."""

    kind: LegalMarkKind
    text: str
    status: LegalMarkStatus = "historical"
    citation: str | None = None


class ParsePage(BaseModel):
    page: int = Field(..., ge=1)
    text: str


class ParseItem(BaseModel):
    item_number: str
    title: str | None = None
    content: str
    page_number: int | None = None
    item_type: str = "item"


class ParseResult(BaseModel):
    """Resultado de extração + estruturação, antes de gravar itens."""

    content_hash: str = Field(..., min_length=64, max_length=64)
    extractor: str
    pages: list[ParsePage]
    items: list[ParseItem]
    marks: list[LegalMark] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_text: str = ""
