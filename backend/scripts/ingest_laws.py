"""
Script de ingestão do corpus jurídico no banco.

Lê os arquivos .txt de backend/data/laws (gerados por download_laws.py)
e popula as tabelas legal_documents/legal_chunks + índice FTS5.

Uso:
    python scripts/ingest_laws.py
"""

import asyncio
import logging
from pathlib import Path

from app.database import async_session_factory, engine, Base
from app.services.rag.loader import ingest_law_text, build_fts_index
from app.models.legal import LegalDocument, LegalChunk  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"

LAWS = [
    {
        "filename": "lei-14133-2021.txt",
        "law_number": "Lei 14.133/2021",
        "law_title": "Lei de Licitações e Contratos Administrativos",
        "source_url": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
        "version": "texto consolidado",
    },
    {
        "filename": "lei-13303-2016.txt",
        "law_number": "Lei 13.303/2016",
        "law_title": "Estatuto Jurídico da Empresa Pública, da Sociedade de Economia Mista e de suas Subsidiárias",
        "source_url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/lei/l13303.htm",
        "version": "texto consolidado",
    },
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        for law in LAWS:
            file_path = DATA_DIR / law["filename"]
            if not file_path.exists():
                logger.warning("Arquivo não encontrado: %s", file_path)
                continue
            content = file_path.read_text(encoding="utf-8")
            await ingest_law_text(
                db,
                content=content,
                law_number=law["law_number"],
                law_title=law["law_title"],
                source_url=law["source_url"],
                version=law["version"],
            )
        await build_fts_index(db)
        await db.commit()
    logger.info("Ingestão do corpus jurídico concluída")


if __name__ == "__main__":
    asyncio.run(main())
