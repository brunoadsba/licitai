"""
Modelos SQLAlchemy do Copiloto (chat consultivo).

Conversas e mensagens são entidades somente-leitura em relação às entidades
de negócio: referenciam documents/analyses apenas como contexto (FK), mas
nunca alteram o estado delas. Compatível com SQLite e PostgreSQL.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ChatConversation(Base):
    """Conversa consultiva do Copiloto sobre um documento/análise."""

    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("ix_chat_conversations_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    analysis_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    context_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    """Mensagem de uma conversa do Copiloto (user ou assistant)."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "role", "id",
            name="uq_chat_messages_conversation_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(10), default="user", nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    grounded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    conversation: Mapped["ChatConversation"] = relationship(
        back_populates="messages"
    )
