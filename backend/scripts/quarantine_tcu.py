"""Marca documentos TCU não verificados como quarantine-0B (não apaga).

Uso (a partir de backend/):
    PYTHONPATH=. python scripts/quarantine_tcu.py
    PYTHONPATH=. python scripts/quarantine_tcu.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update

from app.database import async_session_factory
from app.models.legal import LegalDocument
from app.services.rag.quarantine import (
    QUARANTINE_VERSION,
    UNVERIFIED_TCU_LAWS,
    is_quarantined_law,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("quarantine_tcu")


async def run(*, apply: bool) -> int:
    async with async_session_factory() as db:
        result = await db.execute(select(LegalDocument))
        docs = result.scalars().all()
        alvos = [
            d
            for d in docs
            if is_quarantined_law(d.law_number, d.version)
            or d.law_number in UNVERIFIED_TCU_LAWS
        ]
        logger.info("documentos_tcu_alvo=%d apply=%s", len(alvos), apply)
        for doc in alvos:
            logger.info(
                "alvo law_number=%s version=%s",
                doc.law_number,
                doc.version,
            )
        if not apply:
            logger.info("dry-run: nada alterado; passe --apply para gravar %s", QUARANTINE_VERSION)
            return 0
        if not alvos:
            return 0
        ids = [d.id for d in alvos]
        await db.execute(
            update(LegalDocument)
            .where(LegalDocument.id.in_(ids))
            .values(version=QUARANTINE_VERSION)
        )
        await db.commit()
        logger.info("marcados=%d version=%s", len(ids), QUARANTINE_VERSION)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Quarentena TCU (Fase 0B)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava version=quarantine-0B. Sem esta flag só lista (dry-run).",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(apply=args.apply)))


if __name__ == "__main__":
    main()
