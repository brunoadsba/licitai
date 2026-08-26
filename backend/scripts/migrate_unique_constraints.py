"""
Migração manual: cria o índice único de versões por documento e o índice
parcial de análise ativa por documento.

- `uq_revision_doc_versao`: impede duas revisões com a mesma `versao` para o
  mesmo documento (corrida do max()+1 em create_revision).
- `uq_analyses_active_per_document`: impede duas análises pending/running para
  o mesmo documento (corrida TOCTOU em start_analysis).

Idempotente e compatível com SQLite (CREATE UNIQUE INDEX IF NOT EXISTS) e
PostgreSQL (usa DO block condicional).

Uso:
    python scripts/migrate_unique_constraints.py
"""

import asyncio
import logging

from sqlalchemy import text

from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SQLITE_STATEMENTS = [
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_doc_versao
    ON document_revisions (document_id, versao)
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_analyses_active_per_document
    ON analyses (document_id) WHERE status IN ('pending', 'running')
    """,
]

POSTGRES_STATEMENTS = [
    (
        "uq_revision_doc_versao",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_doc_versao
        ON document_revisions (document_id, versao)
        """,
    ),
    (
        "uq_analyses_active_per_document",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_analyses_active_per_document
        ON analyses (document_id) WHERE status IN ('pending', 'running')
        """,
    ),
]


async def main() -> None:
    """Executa a migração de forma idempotente."""
    try:
        async with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                for statement in SQLITE_STATEMENTS:
                    await conn.execute(text(statement))
                    logger.info("Índice garantido.")
            else:
                for name, statement in POSTGRES_STATEMENTS:
                    exists = (
                        await conn.execute(
                            text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
                            {"name": name},
                        )
                    ).scalar_one_or_none()
                    if exists:
                        logger.info("Índice %s já existe, ignorando", name)
                        continue
                    await conn.execute(text(statement))
                    logger.info("Índice criado: %s", name)

        logger.info("Migração de constraints únicas concluída.")
    finally:
        # Sem dispose o processo fica preso na thread do aiosqlite.
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
