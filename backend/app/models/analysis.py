"""
Modelos SQLAlchemy para análises e correções.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Analysis(Base):
    """Registro de uma análise executada sobre um documento."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'error')"),
        default="pending",
        nullable=False,
    )
    llm_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_items: Mapped[int] = mapped_column(Integer, default=0)

    # Pontuações (0-10)
    score_overall: Mapped[float | None] = mapped_column(
        Numeric(4, 2),
        CheckConstraint("score_overall >= 0 AND score_overall <= 10"),
        nullable=True,
    )
    score_juridical: Mapped[float | None] = mapped_column(
        Numeric(4, 2),
        CheckConstraint("score_juridical >= 0 AND score_juridical <= 10"),
        nullable=True,
    )
    score_technical: Mapped[float | None] = mapped_column(
        Numeric(4, 2),
        CheckConstraint("score_technical >= 0 AND score_technical <= 10"),
        nullable=True,
    )
    score_writing: Mapped[float | None] = mapped_column(
        Numeric(4, 2),
        CheckConstraint("score_writing >= 0 AND score_writing <= 10"),
        nullable=True,
    )
    score_structural: Mapped[float | None] = mapped_column(
        Numeric(4, 2),
        CheckConstraint("score_structural >= 0 AND score_structural <= 10"),
        nullable=True,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(10),
        CheckConstraint("risk_level IN ('baixo', 'medio', 'alto', 'critico')"),
        nullable=True,
    )
    final_opinion: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    document: Mapped["Document"] = relationship(back_populates="analyses")
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Correction(Base):
    """Correção sugerida pela IA para um item do documento."""

    __tablename__ = "corrections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    document_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("category IN ('juridica', 'tecnica', 'redacao', 'estrutural')"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("severity IN ('info', 'baixo', 'medio', 'alto', 'critico')"),
        nullable=False,
    )
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("importance IN ('baixa', 'media', 'alta', 'critica')"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    analysis: Mapped["Analysis"] = relationship(back_populates="corrections")
    document_item: Mapped["DocumentItem"] = relationship(back_populates="corrections")


# Import necessário para referências circulares
from app.models.document import Document, DocumentItem  # noqa: E402, F811
