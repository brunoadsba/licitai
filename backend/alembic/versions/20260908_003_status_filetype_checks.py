"""Alinha CHECKs de analyses.status e documents.file_type ao ORM.

Revision ID: 20260908_003
Revises: 20260908_002
Create Date: 2026-09-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "20260908_003"
down_revision = "20260908_002"
branch_labels = None
depends_on = None


def _drop_check(bind, table: str, needle: str) -> None:
    """Remove constraint CHECK cujo nome ou definição contenha `needle`."""
    dialect = bind.dialect.name
    if dialect != "postgresql":
        return
    rows = bind.execute(
        text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE nsp.nspname = 'public'
              AND rel.relname = :table
              AND con.contype = 'c'
              AND pg_get_constraintdef(con.oid) ILIKE :needle
            """
        ),
        {"table": table, "needle": f"%{needle}%"},
    ).fetchall()
    for (name,) in rows:
        op.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{name}"'))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        _drop_check(bind, "analyses", "status")
        op.execute(
            text(
                "ALTER TABLE analyses ADD CONSTRAINT analyses_status_check "
                "CHECK (status IN ('pending', 'running', 'completed', "
                "'completed_with_errors', 'error'))"
            )
        )
        _drop_check(bind, "documents", "file_type")
        op.execute(
            text(
                "ALTER TABLE documents ADD CONSTRAINT documents_file_type_check "
                "CHECK (file_type IN ('pdf', 'docx', 'odt', 'html'))"
            )
        )
        op.execute(
            text(
                "INSERT INTO schema_meta (key, value) VALUES ('schema_version', '20260908_003') "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            )
        )
    else:
        # SQLite: CHECKs não são alteráveis de forma confiável; schema_meta basta.
        insp = inspect(bind)
        if "schema_meta" in insp.get_table_names():
            op.execute(
                text(
                    "INSERT OR REPLACE INTO schema_meta (key, value) "
                    "VALUES ('schema_version', '20260908_003')"
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _drop_check(bind, "analyses", "status")
        op.execute(
            text(
                "ALTER TABLE analyses ADD CONSTRAINT analyses_status_check "
                "CHECK (status IN ('pending', 'running', 'completed', 'error'))"
            )
        )
        _drop_check(bind, "documents", "file_type")
        op.execute(
            text(
                "ALTER TABLE documents ADD CONSTRAINT documents_file_type_check "
                "CHECK (file_type IN ('pdf', 'docx', 'odt'))"
            )
        )
        op.execute(
            text(
                "UPDATE schema_meta SET value = '20260908_002' WHERE key = 'schema_version'"
            )
        )
