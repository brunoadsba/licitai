"""Modelo jurídico versionado (works, versions, provisions).

Revision ID: 20260924_003
Revises: 20260924_002
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import UUID

revision = "20260924_003"
down_revision = "20260924_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    uuid_type = UUID(as_uuid=True) if bind.dialect.name == "postgresql" else sa.String(36)

    if "legal_works" not in tables:
        op.create_table(
            "legal_works",
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column("law_number", sa.String(80), nullable=False, unique=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("kind", sa.String(40), nullable=False, server_default="lei"),
            sa.Column("issuing_body", sa.String(200), nullable=True),
            sa.Column("sphere", sa.String(40), nullable=True),
            sa.Column("jurisdiction", sa.String(80), nullable=True),
            sa.Column("subject_area", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "legal_versions" not in tables:
        op.create_table(
            "legal_versions",
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column("work_id", uuid_type, sa.ForeignKey("legal_works.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_url", sa.String(500), nullable=True),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("wording", sa.String(40), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="unpublished"),
            sa.Column("validity_start", sa.Date(), nullable=True),
            sa.Column("validity_end", sa.Date(), nullable=True),
            sa.Column("amending_norm", sa.String(200), nullable=True),
            sa.Column("validation_source", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "legal_provisions" not in tables:
        op.create_table(
            "legal_provisions",
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column("version_id", uuid_type, sa.ForeignKey("legal_versions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("work_id", uuid_type, sa.ForeignKey("legal_works.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_id", uuid_type, sa.ForeignKey("legal_provisions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("path", sa.String(200), nullable=False),
            sa.Column("article", sa.String(40), nullable=True),
            sa.Column("paragraph", sa.String(40), nullable=True),
            sa.Column("inciso", sa.String(20), nullable=True),
            sa.Column("alinea", sa.String(10), nullable=True),
            sa.Column("item", sa.String(20), nullable=True),
            sa.Column("canonical_text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="vigente"),
            sa.Column("provision_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("version_id", "path", name="uq_provision_version_path"),
        )
        op.create_index(
            "uq_provision_vigente_path",
            "legal_provisions",
            ["work_id", "path"],
            unique=True,
            postgresql_where=sa.text("status = 'vigente'"),
            sqlite_where=sa.text("status = 'vigente'"),
        )

    if "legal_id_map" not in tables:
        op.create_table(
            "legal_id_map",
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column("old_chunk_id", uuid_type, sa.ForeignKey("legal_chunks.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("provision_id", uuid_type, sa.ForeignKey("legal_provisions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("legal_document_id", uuid_type, sa.ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False),
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260924_003' "
                "WHERE key = 'schema_version'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for name in ("legal_id_map", "legal_provisions", "legal_versions", "legal_works"):
        if name in tables:
            op.drop_table(name)
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260924_002' "
                "WHERE key = 'schema_version'"
            )
        )
