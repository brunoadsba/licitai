"""
Schemas Pydantic para análises e relatórios.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class AnalysisStartResponse(BaseModel):
    """Resposta ao iniciar uma análise."""
    analysis_id: uuid.UUID
    message: str


class AnalysisResponse(BaseModel):
    """Resposta resumida de uma análise."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    llm_provider: str
    llm_model: str
    total_items: int
    analyzed_items: int
    score_overall: float | None = None
    risk_level: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class AnalysisDetailResponse(BaseModel):
    """Detalhes completos de uma análise com correções."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    llm_provider: str
    llm_model: str
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
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    corrections: list[CorrectionResponse] = []


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
    analyzed_at: datetime | None = None
