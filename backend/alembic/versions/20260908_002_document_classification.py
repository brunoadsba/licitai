"""Add documents.classification for sigiloso privacy gate.

Revision ID: 20260908_002
Revises: 20260908_001
Create Date: 2026-09-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260908_002"
down_revision = "20260908_001"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if not _has_column(bind, "documents", "classification"):
        op.add_column(
            "documents",
            sa.Column("classification", sa.String(length=50), nullable=True),
        )
    # Manter schema_meta alinhado ao head (readyz).
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "INSERT INTO schema_meta (key, value) VALUES ('schema_version', '20260908_002') "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            )
        )
    else:
        op.execute(
            sa.text(
                "INSERT OR REPLACE INTO schema_meta (key, value) "
                "VALUES ('schema_version', '20260908_002')"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "documents", "classification"):
        op.drop_column("documents", "classification")
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "UPDATE schema_meta SET value = '20260908_001' WHERE key = 'schema_version'"
            )
        )
    else:
        op.execute(
            sa.text(
                "INSERT OR REPLACE INTO schema_meta (key, value) "
                "VALUES ('schema_version', '20260908_001')"
            )
        )
