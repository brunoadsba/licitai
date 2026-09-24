"""Cria retrieval_runs e liga chat_messages à recuperação.

Revision ID: 20260924_001
Revises: 20260908_003
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260924_001"
down_revision = "20260908_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "retrieval_runs" not in tables:
        op.create_table(
            "retrieval_runs",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("request_id", sa.String(64), nullable=True),
            sa.Column("operation_type", sa.String(20), nullable=False),
            sa.Column("query_hash", sa.String(64), nullable=False),
            sa.Column("corpus_version", sa.String(64), nullable=False),
            sa.Column("embedding_model", sa.String(100), nullable=True),
            sa.Column("rerank_model", sa.String(100), nullable=True),
            sa.Column("params", JSONB, nullable=True),
            sa.Column("retrieved_ids", JSONB, nullable=False, server_default="[]"),
            sa.Column("scores", JSONB, nullable=False, server_default="[]"),
            sa.Column("filters", JSONB, nullable=True),
            sa.Column("classification", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_retrieval_runs_created_at", "retrieval_runs", ["created_at"]
        )
        op.create_index(
            "ix_retrieval_runs_operation_type",
            "retrieval_runs",
            ["operation_type"],
        )

    if "chat_messages" in tables:
        columns = {col["name"] for col in inspector.get_columns("chat_messages")}
        if "retrieval_run_id" not in columns:
            op.add_column(
                "chat_messages",
                sa.Column("retrieval_run_id", sa.String(36), nullable=True),
            )

    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260924_001' "
                "WHERE key = 'schema_version'"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "chat_messages" in tables:
        columns = {col["name"] for col in inspector.get_columns("chat_messages")}
        if "retrieval_run_id" in columns:
            op.drop_column("chat_messages", "retrieval_run_id")

    if "retrieval_runs" in tables:
        op.drop_index("ix_retrieval_runs_operation_type", table_name="retrieval_runs")
        op.drop_index("ix_retrieval_runs_created_at", table_name="retrieval_runs")
        op.drop_table("retrieval_runs")

    if bind.dialect.name == "postgresql":
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260908_003' "
                "WHERE key = 'schema_version'"
            )
        )
