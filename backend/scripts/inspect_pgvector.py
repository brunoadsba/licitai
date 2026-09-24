"""Inspeciona pgvector e FTS no Postgres de homologação (Fase 5)."""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def inspect() -> dict:
    engine = create_async_engine(settings.database_url)
    report: dict = {"dialect": None, "pgvector": {}, "fts": {}, "plan": None}
    async with engine.connect() as conn:
        report["dialect"] = conn.dialect.name
        if conn.dialect.name != "postgresql":
            return report
        ext = (
            await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
        ).scalar_one_or_none()
        col = (
            await conn.execute(
                text(
                    "SELECT data_type, udt_name FROM information_schema.columns "
                    "WHERE table_name = 'legal_chunks' AND column_name = 'embedding_vector'"
                )
            )
        ).first()
        idx = (
            await conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'legal_chunks' AND indexdef ILIKE '%embedding_vector%'"
                )
            )
        ).first()
        filled = (
            await conn.execute(
                text(
                    "SELECT COUNT(*) FROM legal_chunks WHERE embedding_vector IS NOT NULL"
                )
            )
        ).scalar()
        tsv = (
            await conn.execute(
                text(
                    "SELECT COUNT(*) FROM legal_chunks WHERE search_tsv IS NOT NULL"
                )
            )
        ).scalar()
        tsv_idx = (
            await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'legal_chunks' AND indexname = 'ix_legal_chunks_search_tsv'"
                )
            )
        ).scalar_one_or_none()
        report["pgvector"] = {
            "extension_version": ext,
            "column": dict(col._mapping) if col else None,
            "index": dict(idx._mapping) if idx else None,
            "rows_with_vector": int(filled or 0),
        }
        report["fts"] = {
            "rows_with_tsv": int(tsv or 0),
            "gin_index": tsv_idx,
        }
        try:
            plan_rows = (
                await conn.execute(
                    text(
                        "EXPLAIN (FORMAT JSON) "
                        "SELECT id FROM legal_chunks "
                        "WHERE search_tsv @@ plainto_tsquery('portuguese', 'licitacao') "
                        "LIMIT 5"
                    )
                )
            ).scalar()
            report["plan"] = plan_rows
        except Exception as exc:
            report["plan_error"] = str(exc)
    await engine.dispose()
    return report


if __name__ == "__main__":
    print(json.dumps(asyncio.run(inspect()), ensure_ascii=False, indent=2, default=str))
