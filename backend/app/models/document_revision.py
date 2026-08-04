"""
Modelo de dados para Histórico e Versionamento de Edições de Documentos (Single-User).
"""

import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentRevision(Base):
    """
    Representa um snapshot / rascunho salvo do documento TR em um determinado ponto no tempo.
    """

    __tablename__ = "document_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    rotulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    items_snapshot: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relacionamento com Document
    document = relationship("Document", backref="revisions")

    def __repr__(self) -> str:
        return f"<DocumentRevision v{self.versao} '{self.rotulo}' doc_id={self.document_id}>"
