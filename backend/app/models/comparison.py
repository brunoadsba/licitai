"""
Modelos SQLAlchemy para o módulo de auditoria TR × Propostas.

- Fornecedor: empresa que envia proposta.
- Molde: conjunto de regras configuráveis (âncoras) aplicado ao TR.
- Comparacao: execução de comparação entre TR e propostas de fornecedores.
- ComparacaoResultado: status por regra/fornecedor (OK/FALHA/ATENÇÃO).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Fornecedor(Base):
    """Fornecedor que participa da licitação com uma proposta."""

    __tablename__ = "fornecedores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(18), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    documentos: Mapped[list["Document"]] = relationship(
        "Document", back_populates="fornecedor"
    )
    resultados: Mapped[list["ComparacaoResultado"]] = relationship(
        "ComparacaoResultado", back_populates="fornecedor",
        cascade="all, delete-orphan",
    )


class Molde(Base):
    """Molde de TR — conjunto de regras configuráveis em JSON."""

    __tablename__ = "moldes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    comparacoes: Mapped[list["Comparacao"]] = relationship(
        "Comparacao", back_populates="molde"
    )


class Comparacao(Base):
    """Execução de uma comparação entre TR e propostas."""

    __tablename__ = "comparacoes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tr_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    molde_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("moldes.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'error')"
        ),
        default="pending",
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relacionamentos
    tr: Mapped["Document"] = relationship("Document")
    molde: Mapped["Molde"] = relationship(back_populates="comparacoes")
    resultados: Mapped[list["ComparacaoResultado"]] = relationship(
        "ComparacaoResultado", back_populates="comparacao",
        cascade="all, delete-orphan",
    )


class ComparacaoResultado(Base):
    """Resultado de uma regra para um fornecedor (status e valores)."""

    __tablename__ = "comparacao_resultados"

    __table_args__ = (
        UniqueConstraint(
            "comparacao_id", "fornecedor_id", "regra_id",
            name="uq_comparacao_fornecedor_regra",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comparacoes.id", ondelete="CASCADE"),
        nullable=False,
    )
    fornecedor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fornecedores.id", ondelete="CASCADE"),
        nullable=False,
    )
    regra_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("status IN ('ok', 'falha', 'atencao')"),
        nullable=False,
    )
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_tr: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valor_proposta: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    comparacao: Mapped["Comparacao"] = relationship(
        back_populates="resultados"
    )
    fornecedor: Mapped["Fornecedor"] = relationship(
        back_populates="resultados"
    )


# Import necessários para referências circulares
from app.models.document import Document  # noqa: E402, F811
