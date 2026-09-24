"""FTS PostgreSQL em legal_chunks (unaccent + tsvector).

Revision ID: 20260924_004
Revises: 20260924_003
Create Date: 2026-09-24
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, text

revision = "20260924_004"
down_revision = "20260924_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    op.execute(
        text(
            "CREATE OR REPLACE FUNCTION licitai_unaccent(t text) "
            "RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ "
            "SELECT public.unaccent('public.unaccent', coalesce(t, '')) $$"
        )
    )
    inspector = inspect(bind)
    if "legal_chunks" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("legal_chunks")}
        if "search_tsv" not in cols:
            op.execute(text("ALTER TABLE legal_chunks ADD COLUMN search_tsv tsvector"))
        op.execute(
            text(
                "UPDATE legal_chunks SET search_tsv = "
                "to_tsvector('portuguese', licitai_unaccent(chunk_text)) "
                "WHERE search_tsv IS NULL"
            )
        )
        op.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_legal_chunks_search_tsv "
                "ON legal_chunks USING GIN (search_tsv)"
            )
        )
        op.execute(text("DROP TRIGGER IF EXISTS trg_legal_chunks_search_tsv ON legal_chunks"))
        op.execute(
            text(
                "CREATE OR REPLACE FUNCTION legal_chunks_tsv_update() "
                "RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN NEW.search_tsv := to_tsvector('portuguese', "
                "licitai_unaccent(NEW.chunk_text)); RETURN NEW; END; $$"
            )
        )
        op.execute(
            text(
                "CREATE TRIGGER trg_legal_chunks_search_tsv "
                "BEFORE INSERT OR UPDATE OF chunk_text ON legal_chunks "
                "FOR EACH ROW EXECUTE FUNCTION legal_chunks_tsv_update()"
            )
        )
    op.execute(
        text(
            "UPDATE schema_meta SET value = '20260924_004' "
            "WHERE key = 'schema_version'"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(text("DROP TRIGGER IF EXISTS trg_legal_chunks_search_tsv ON legal_chunks"))
    op.execute(text("DROP FUNCTION IF EXISTS legal_chunks_tsv_update()"))
    op.execute(text("DROP INDEX IF EXISTS ix_legal_chunks_search_tsv"))
    inspector = inspect(bind)
    if "legal_chunks" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("legal_chunks")}
        if "search_tsv" in cols:
            op.execute(text("ALTER TABLE legal_chunks DROP COLUMN search_tsv"))
    op.execute(
        text(
            "UPDATE schema_meta SET value = '20260924_003' "
            "WHERE key = 'schema_version'"
        )
    )
