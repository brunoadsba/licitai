"""
Migração idempotente para adicionar as colunas agent_origin e analysis_mode.
Suporta SQLite e PostgreSQL.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adicionar pasta backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_agent_columns")


async def run_migration():
    logger.info("Iniciando migração de colunas para Múltiplos Agentes...")
    async with engine.begin() as conn:
        dialect = conn.dialect.name
        logger.info("Dialeto do Banco de Dados: %s", dialect)

        # 1. Adicionar agent_origin em corrections
        try:
            if dialect == "sqlite":
                await conn.execute(
                    text(
                        "ALTER TABLE corrections ADD COLUMN agent_origin VARCHAR(20);"
                    )
                )
            else:
                await conn.execute(
                    text(
                        "ALTER TABLE corrections ADD COLUMN IF NOT EXISTS agent_origin VARCHAR(20);"
                    )
                )
            logger.info("Coluna 'agent_origin' adicionada à tabela 'corrections'.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("Coluna 'agent_origin' já existe na tabela 'corrections'.")
            else:
                logger.warning("Aviso ao adicionar agent_origin: %s", e)

        # 2. Adicionar analysis_mode em analyses
        try:
            if dialect == "sqlite":
                await conn.execute(
                    text(
                        "ALTER TABLE analyses ADD COLUMN analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent';"
                    )
                )
            else:
                await conn.execute(
                    text(
                        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent';"
                    )
                )
            logger.info("Coluna 'analysis_mode' adicionada à tabela 'analyses'.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                logger.info("Coluna 'analysis_mode' já existe na tabela 'analyses'.")
            else:
                logger.warning("Aviso ao adicionar analysis_mode: %s", e)

    logger.info("Migração concluída com sucesso!")


if __name__ == "__main__":
    asyncio.run(run_migration())
