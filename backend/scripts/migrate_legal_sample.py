"""Migra amostra do corpus legado para o modelo versionado (Fase 4).

Não troca o índice de busca. Uso:

    PYTHONPATH=. python scripts/migrate_legal_sample.py
"""

from __future__ import annotations

import asyncio
import logging

from app.database import async_session_factory
from app.services.legal_model.migrate import migrate_sample

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    async with async_session_factory() as db:
        reports = await migrate_sample(db)
        await db.commit()
    for report in reports:
        logger.info(
            "%s chunks=%s provisions=%s mapped=%s missing=%s",
            report.law_number,
            report.old_chunks,
            report.new_provisions,
            report.mapped,
            report.missing_articles,
        )


if __name__ == "__main__":
    asyncio.run(main())
