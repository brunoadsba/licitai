"""
Migração manual: adiciona colunas de revisão à tabela `corrections`.

Adiciona `review_status`, `review_note` e `reviewed_at` caso ainda não existam.
Idempotente e compatível com SQLite e PostgreSQL.

Uso:
    python scripts/migrate_review_columns.py
"""

import asyncio
import logging

from sqlalchemy import text

from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

STATEMENTS = [
    (
        "review_status",
        "ALTER TABLE corrections ADD COLUMN review_status "
        "VARCHAR(20) DEFAULT 'pendente' NOT NULL",
    ),
    (
        "review_note",
        "ALTER TABLE corrections ADD COLUMN review_note TEXT",
    ),
    (
        "reviewed_at",
        "ALTER TABLE corrections ADD COLUMN reviewed_at "
        "TIMESTAMP WITH TIME ZONE",
    ),
]


async def _existing_columns(table: str) -> set[str]:
    """Retorna os nomes das colunas existentes na tabela."""
    async with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).all()
            return {row[1] for row in rows}
        rows = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table"
            ),
            {"table": table},
        )
        return {row[0] for row in rows}


async def main() -> None:
    """Executa a migração de forma idempotente."""
    existing = await _existing_columns("corrections")

    async with engine.begin() as conn:
        for column, statement in STATEMENTS:
            if column in existing:
                logger.info("Coluna %s já existe, ignorando", column)
                continue
            await conn.execute(text(statement))
            logger.info("Coluna adicionada: %s", column)

    logger.info("Migração de revisão concluída.")


if __name__ == "__main__":
    asyncio.run(main())
