"""
Modelos SQLAlchemy para documentos e seus itens estruturados.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    """Documento enviado pelo usuário (TR)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename_original: Mapped[str] = mapped_column(String(500), nullable=False)
    filename_stored: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    file_type: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("file_type IN ('pdf', 'docx', 'odt')"),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger, CheckConstraint("file_size_bytes > 0"), nullable=False
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('uploaded', 'parsing', 'parsed', 'analyzing', 'completed', 'error')"
        ),
        default="uploaded",
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relacionamentos
    items: Mapped[list["DocumentItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan",
        order_by="DocumentItem.item_order"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentItem(Base):
    """Item estruturado extraído de um documento."""

    __tablename__ = "document_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    item_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "item_type IN ('section', 'item', 'subitem', 'table', 'annex')"
        ),
        default="item",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    document: Mapped["Document"] = relationship(back_populates="items")
    corrections: Mapped[list["Correction"]] = relationship(
        "Correction", back_populates="document_item", cascade="all, delete-orphan"
    )
