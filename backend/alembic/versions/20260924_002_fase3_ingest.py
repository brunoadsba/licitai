"""Metadados de ingestão jurídica (hash, origem, status).

Revision ID: 20260924_002
Revises: 20260924_001
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260924_002"
down_revision = "20260924_001"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("content_hash", sa.Column("content_hash", sa.String(64), nullable=True)),
    ("origin", sa.Column("origin", sa.String(200), nullable=True)),
    ("collected_at", sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True)),
    ("ingest_status", sa.Column("ingest_status", sa.String(20), nullable=False, server_default="published")),
    ("last_error", sa.Column("last_error", sa.Text(), nullable=True)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "legal_documents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("legal_documents")}
    for name, column in _COLUMNS:
        if name not in existing:
            op.add_column("legal_documents", column)
    if "ingest_manifest" not in existing:
        manifest_type = JSONB() if bind.dialect.name == "postgresql" else sa.JSON()
        op.add_column("legal_documents", sa.Column("ingest_manifest", manifest_type, nullable=True))
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE legal_documents SET ingest_status = 'published' "
                "WHERE ingest_status IS NULL"
            )
        )
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260924_002' "
                "WHERE key = 'schema_version'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "legal_documents" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("legal_documents")}
    for name in (
        "ingest_manifest",
        "last_error",
        "ingest_status",
        "collected_at",
        "origin",
        "content_hash",
    ):
        if name in existing:
            op.drop_column("legal_documents", name)
    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260924_001' "
                "WHERE key = 'schema_version'"
            )
        )
