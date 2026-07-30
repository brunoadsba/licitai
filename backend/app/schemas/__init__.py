"""Pacote de schemas Pydantic."""

from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentItemResponse,
    DocumentListResponse,
    DocumentDetailResponse,
)
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisDetailResponse,
    CorrectionResponse,
    ReportResponse,
    AnalysisStartResponse,
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
