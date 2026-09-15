"""Schemas do revisor-assistente — sugestão por correção (consultivo, fail-closed)."""

from pydantic import BaseModel, Field


class ReviewSuggestion(BaseModel):
    correction_id: str
    suggestion: str = Field(description="aprovar | rejeitar | ajustar")
    confidence: float = Field(ge=0, le=1, description="0–1")
    reason: str
    evidence: dict
    grounded: bool | None = None
    legal_valid: bool | None = None
    has_placeholder: bool = False
    fail_closed: bool = False


class ReviewSuggestionsResponse(BaseModel):
    analysis_id: str
    total: int
    pending: int
    suggestions: list[ReviewSuggestion]
