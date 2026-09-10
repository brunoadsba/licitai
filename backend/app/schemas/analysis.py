"""
Schemas Pydantic para análises e relatórios.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _ensure_tz(v: datetime) -> datetime:
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


AwareDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]

ReviewStatusLiteral = Literal["pendente", "aprovada", "rejeitada", "ajustada"]


class CorrectionResponse(BaseModel):
    """Resposta para uma correção individual."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_item_id: uuid.UUID
    category: str
    severity: str
    situation: str
    problem: str
    risk: str
    original_text: str
    suggested_text: str
    justification: str
    legal_basis: str | None = None
    importance: str
    agent_origin: str | None = None
    review_status: str = "pendente"
    review_note: str | None = None
    reviewed_at: AwareDatetime | None = None


class CorrectionReviewUpdate(BaseModel):
    """Payload para revisão humana de uma correção (SEI)."""

    review_status: ReviewStatusLiteral
    review_note: str | None = Field(default=None, max_length=4000)
    suggested_text: str | None = Field(default=None, max_length=50_000)
    justification: str | None = Field(default=None, max_length=50_000)

    @model_validator(mode="after")
    def validate_ajustada_fields(self) -> "CorrectionReviewUpdate":
        if self.review_status == "ajustada" and not (
            self.suggested_text or self.justification or self.review_note
        ):
            raise ValueError(
                "Para status 'ajustada', informe suggested_text, justification ou review_note."
            )
        return self


class AnalysisStartRequest(BaseModel):
    """Payload para iniciar uma análise."""

    mode: Literal["multi_agent", "single", "economic"] = "economic"


class AnalysisStartResponse(BaseModel):
    """Resposta ao iniciar uma análise."""
    analysis_id: uuid.UUID
    job_id: uuid.UUID | None = None
    message: str


class Art6ChecklistItem(BaseModel):
    """Status de uma alínea do Art. 6º, XXIII."""

    key: str
    alinea: str
    label: str
    status: Literal["present", "missing", "uncertain"]


class PendingSummaryItem(BaseModel):
    document_id: uuid.UUID
    analysis_id: uuid.UUID
    filename: str
    pending_priority: int
    status: str


class PendingSummaryResponse(BaseModel):
    total: int
    items: list[PendingSummaryItem]


class CorrectedHtmlSkip(BaseModel):
    correction_id: uuid.UUID
    reason: str


class AnalysisResponse(BaseModel):
    """Resposta resumida de uma análise."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    llm_provider: str
    llm_model: str
    analysis_mode: str = "multi_agent"
    total_items: int
    analyzed_items: int
    score_overall: float | None = None
    risk_level: str | None = None
    created_at: AwareDatetime
    completed_at: AwareDatetime | None = None


class AnalysisDetailResponse(BaseModel):
    """Detalhes completos de uma análise com correções."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    llm_provider: str
    llm_model: str
    analysis_mode: str = "multi_agent"
    total_items: int
    analyzed_items: int
    score_overall: float | None = None
    score_juridical: float | None = None
    score_technical: float | None = None
    score_writing: float | None = None
    score_structural: float | None = None
    risk_level: str | None = None
    final_opinion: str | None = None
    error_message: str | None = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    created_at: AwareDatetime
    corrections: list[CorrectionResponse] = []
    tokens_estimated: int | None = None
    art6_checklist: list[Art6ChecklistItem] = []


class ScoreDetail(BaseModel):
    """Detalhe de uma pontuação no relatório."""
    label: str
    score: float | None = None
    max_score: float = 10.0


class ReportResponse(BaseModel):
    """Relatório final completo."""
    analysis_id: uuid.UUID
    document_name: str
    document_id: uuid.UUID
    status: str
    scores: list[ScoreDetail] = []
    risk_level: str | None = None
    total_corrections: int = 0
    corrections_by_category: dict[str, int] = {}
    corrections_by_severity: dict[str, int] = {}
    corrections: list[CorrectionResponse] = []
    final_opinion: str | None = None
    analyzed_at: AwareDatetime | None = None
    tokens_estimated: int | None = None
    art6_checklist: list[Art6ChecklistItem] = []


class SeiPackEntry(BaseModel):
    """Uma entrada do pacote SEI."""

    correction_id: uuid.UUID
    item_number: str
    title: str | None = None
    suggested_text: str
    justification: str
    legal_basis: str | None = None
    severity: str
    category: str


class SeiPackResponse(BaseModel):
    """Pacote ordenado para colar no SEI."""

    analysis_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    total: int
    text: str
    entries: list[SeiPackEntry]


class CorrectedHtmlResponse(BaseModel):
    """TR HTML com correções aprovadas/ajustadas aplicadas."""

    document_id: uuid.UUID
    analysis_id: uuid.UUID
    document_name: str
    applied_corrections: int
    skipped_corrections: list[CorrectedHtmlSkip] = []
    html: str
