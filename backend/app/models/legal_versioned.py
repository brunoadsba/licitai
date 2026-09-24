"""Modelo jurídico versionado (Fase 4). Não substitui legal_documents."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LegalWork(Base):
    """Norma estável (lei, regulamento, jurisprudência)."""

    __tablename__ = "legal_works"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    law_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="lei")
    issuing_body: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sphere: Mapped[str | None] = mapped_column(String(40), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(80), nullable=True)
    subject_area: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    versions: Mapped[list["LegalVersion"]] = relationship(
        back_populates="work", cascade="all, delete-orphan"
    )


class LegalVersion(Base):
    """Versão imutável de uma norma."""

    __tablename__ = "legal_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    work_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_works.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    wording: Mapped[str] = mapped_column(String(40), default="consolidada")
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('published', 'superseded', 'unpublished')"),
        default="unpublished",
        nullable=False,
    )
    validity_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    validity_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    amending_norm: Mapped[str | None] = mapped_column(String(200), nullable=True)
    validation_source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    work: Mapped[LegalWork] = relationship(back_populates="versions")
    provisions: Mapped[list["LegalProvision"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class LegalProvision(Base):
    """Dispositivo de uma versão (artigo, parágrafo, inciso, alínea)."""

    __tablename__ = "legal_provisions"
    __table_args__ = (
        UniqueConstraint("version_id", "path", name="uq_provision_version_path"),
        Index(
            "uq_provision_vigente_path",
            "work_id",
            "path",
            unique=True,
            sqlite_where=text("status = 'vigente'"),
            postgresql_where=text("status = 'vigente'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_works.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_provisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    path: Mapped[str] = mapped_column(String(200), nullable=False)
    article: Mapped[str | None] = mapped_column(String(40), nullable=True)
    paragraph: Mapped[str | None] = mapped_column(String(40), nullable=True)
    inciso: Mapped[str | None] = mapped_column(String(20), nullable=True)
    alinea: Mapped[str | None] = mapped_column(String(10), nullable=True)
    item: Mapped[str | None] = mapped_column(String(20), nullable=True)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('vigente', 'historical', 'vetado')"),
        default="vigente",
        nullable=False,
    )
    provision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    version: Mapped[LegalVersion] = relationship(back_populates="provisions")


class LegalIdMap(Base):
    """Mapeia chunk legado → dispositivo novo. O índice antigo permanece."""

    __tablename__ = "legal_id_map"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    old_chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    provision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_provisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    legal_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
