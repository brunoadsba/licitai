"""Baseline confiabilidade: evidence, manifest, índices, jobs, schema_version.

Revision ID: 20260908_001
Revises:
Create Date: 2026-09-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "20260908_001"
down_revision = None
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def _has_index(bind, table: str, name: str) -> bool:
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return False
    return name in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if not _has_column(bind, "documents", "generation_manifest"):
        op.add_column(
            "documents",
            sa.Column("generation_manifest", sa.JSON(), nullable=True),
        )

    if not _has_column(bind, "document_items", "created_at"):
        op.add_column(
            "document_items",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
            ),
        )

    if not _has_column(bind, "document_items", "archived_at"):
        op.add_column(
            "document_items",
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_column(bind, "corrections", "evidence"):
        op.add_column(
            "corrections",
            sa.Column("evidence", sa.JSON(), nullable=True),
        )

    # Alinhar legal_chunks.metadata (SQL) ↔ doc_metadata (ORM)
    if _has_column(bind, "legal_chunks", "metadata") and not _has_column(
        bind, "legal_chunks", "doc_metadata"
    ):
        if dialect == "postgresql":
            op.alter_column("legal_chunks", "metadata", new_column_name="doc_metadata")
        else:
            op.execute(
                text(
                    "ALTER TABLE legal_chunks RENAME COLUMN metadata TO doc_metadata"
                )
            )
    elif not _has_column(bind, "legal_chunks", "doc_metadata") and not _has_column(
        bind, "legal_chunks", "metadata"
    ):
        op.add_column(
            "legal_chunks",
            sa.Column("doc_metadata", sa.JSON(), nullable=True),
        )

    if not _has_column(bind, "legal_chunks", "embedding_model"):
        op.add_column(
            "legal_chunks",
            sa.Column("embedding_model", sa.String(100), nullable=True),
        )
    if not _has_column(bind, "legal_chunks", "embedding_dim"):
        op.add_column(
            "legal_chunks",
            sa.Column("embedding_dim", sa.Integer(), nullable=True),
        )

    if dialect == "postgresql":
        if not _has_index(bind, "analyses", "uq_analyses_active_per_document"):
            op.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_analyses_active_per_document "
                    "ON analyses (document_id) "
                    "WHERE status IN ('pending', 'running')"
                )
            )
        if not _has_index(bind, "document_revisions", "uq_revision_doc_versao"):
            op.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_doc_versao "
                    "ON document_revisions (document_id, versao)"
                )
            )
        # pgvector column opcional (extensão já no init.sql)
        op.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        cols = {c["name"] for c in inspect(bind).get_columns("legal_chunks")}
        if "embedding_vector" not in cols:
            op.execute(
                text(
                    "ALTER TABLE legal_chunks "
                    "ADD COLUMN IF NOT EXISTS embedding_vector vector(3072)"
                )
            )
            op.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_legal_chunks_embedding_hnsw "
                    "ON legal_chunks USING hnsw (embedding_vector vector_cosine_ops)"
                )
            )
        op.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_legal_chunks_fts "
                "ON legal_chunks USING gin (to_tsvector('portuguese', coalesce(chunk_text, '')))"
            )
        )
    else:
        if not _has_index(bind, "analyses", "uq_analyses_active_per_document"):
            op.create_index(
                "uq_analyses_active_per_document",
                "analyses",
                ["document_id"],
                unique=True,
                sqlite_where=sa.text("status IN ('pending', 'running')"),
            )

    # Tabela jobs (fila durável)
    insp = inspect(bind)
    if "jobs" not in insp.get_table_names():
        op.create_table(
            "jobs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_jobs_status", "jobs", ["status"])
        op.create_index("idx_jobs_type_status", "jobs", ["type", "status"])

    # Schema version tracking
    if "schema_meta" not in insp.get_table_names():
        op.create_table(
            "schema_meta",
            sa.Column("key", sa.String(64), primary_key=True),
            sa.Column("value", sa.String(255), nullable=False),
        )
    op.execute(
        text(
            "INSERT INTO schema_meta (key, value) VALUES ('schema_version', '20260908_001') "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            if dialect == "postgresql"
            else (
                "INSERT OR REPLACE INTO schema_meta (key, value) "
                "VALUES ('schema_version', '20260908_001')"
            )
        )
    )

    # Snapshots / lineage em analyses e comparacoes
    if not _has_column(bind, "analyses", "run_snapshot"):
        op.add_column("analyses", sa.Column("run_snapshot", sa.JSON(), nullable=True))
    if not _has_column(bind, "analyses", "status"):
        pass
    # Expandir status allowed via app layer; add completed_with_errors support in app
    if not _has_column(bind, "comparacoes", "run_snapshot"):
        op.add_column("comparacoes", sa.Column("run_snapshot", sa.JSON(), nullable=True))
    if not _has_column(bind, "comparacoes", "propostas_ids"):
        op.add_column("comparacoes", sa.Column("propostas_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Downgrade intencional mínimo — ambiente single-user.
    pass
