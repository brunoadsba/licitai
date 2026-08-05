"""
Deduplicação de `comparacao_resultados` antes da constraint UNIQUE.

Remove linhas duplicadas (mesma combinação comparacao_id, fornecedor_id, regra_id),
mantendo apenas a de menor `id`. Idempotente e compatível com SQLite e PostgreSQL.

Uso:
    python scripts/dedupe_comparacao_resultados.py
"""

import asyncio
import logging

from sqlalchemy import text

from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEDUPE_SQL = """
    DELETE FROM comparacao_resultados
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM comparacao_resultados
        GROUP BY comparacao_id, fornecedor_id, regra_id
    )
"""


async def main() -> None:
    """Executa a deduplicação e reporta o total removido."""
    async with engine.begin() as conn:
        result = await conn.execute(text(DEDUPE_SQL))
        removed = result.rowcount

    if removed:
        logger.info("%d linhas duplicadas removidas de comparacao_resultados.", removed)
    else:
        logger.info("Nenhuma duplicata encontrada em comparacao_resultados.")


if __name__ == "__main__":
    asyncio.run(main())
