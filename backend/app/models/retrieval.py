"""Registro de uma recuperação RAG (análise, chat ou avaliação)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RetrievalRun(Base):
    """Uma execução de retrieve() com IDs e parâmetros persistidos."""

    __tablename__ = "retrieval_runs"
    __table_args__ = (
        Index("ix_retrieval_runs_created_at", "created_at"),
        Index("ix_retrieval_runs_operation_type", "operation_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rerank_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieved_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    scores: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
