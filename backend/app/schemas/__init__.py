"""Pacote de schemas Pydantic."""

from app.schemas.analysis import (
    AnalysisDetailResponse,
    AnalysisResponse,
    AnalysisStartResponse,
    CorrectionResponse,
    ReportResponse,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentItemResponse,
    DocumentListResponse,
    DocumentResponse,
)

__all__ = [
    "DocumentCreate",
    "DocumentResponse",
    "DocumentItemResponse",
    "DocumentListResponse",
    "DocumentDetailResponse",
    "AnalysisResponse",
    "AnalysisDetailResponse",
    "CorrectionResponse",
    "ReportResponse",
    "AnalysisStartResponse",
]
