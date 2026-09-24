"""Copia legal_chunks.embedding (JSON) → embedding_vector. Sem HNSW.

Uso (Compose):
  docker compose exec -T backend python scripts/backfill_embedding_vector.py
  docker compose exec -T backend python scripts/backfill_embedding_vector.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def _run(apply: bool) -> int:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        if conn.dialect.name != "postgresql":
            print("somente PostgreSQL")
            return 1
        pending = (
            await conn.execute(
                text(
                    "SELECT id, embedding FROM legal_chunks "
                    "WHERE embedding IS NOT NULL AND embedding <> '' "
                    "AND embedding_vector IS NULL"
                )
            )
        ).all()
        print(f"pendentes={len(pending)}")
        if not apply:
            return 0
        filled = 0
        for row_id, raw in pending:
            try:
                vec = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(vec, list) or not vec:
                continue
            literal = "[" + ",".join(str(float(x)) for x in vec) + "]"
            await conn.execute(
                text(
                    "UPDATE legal_chunks SET embedding_vector = CAST(:v AS vector) "
                    "WHERE id = :id"
                ),
                {"v": literal, "id": row_id},
            )
            filled += 1
        print(f"preenchidos={filled}")
    await engine.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    return asyncio.run(_run(parser.parse_args().apply))


if __name__ == "__main__":
    raise SystemExit(main())
