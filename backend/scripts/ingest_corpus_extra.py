"""
Script de ingestão de corpus jurídico extra (RAG Fase 4.2).

Lê acórdãos do JurisTCU (backend/data/juristcu/*.txt) e instruções do RILC
da CODEBA (backend/data/rilc/*.txt) e popula legal_documents/legal_chunks,
usando o chunker genérico (documentos sem estrutura de "Art.").

Formato dos arquivos:
    # Acórdão 1234/2024
    # Título: Prestação de contas
    <parágrafos do documento...>

Uso:
    python scripts/ingest_corpus_extra.py
"""

import asyncio
import logging
from pathlib import Path

from app.database import Base, async_session_factory, engine
from app.models.legal import LegalDocument, LegalChunk  # noqa: F401
from app.services.rag.loader import build_fts_index, ingest_extra_document

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FONTES = [
    {
        "nome": "JurisTCU",
        "diretorio": "juristcu",
        "prefixo_id": "Acórdão",
    },
    {
        "nome": "RILC",
        "diretorio": "rilc",
        "prefixo_id": "RILC",
    },
]


def _ler_metadata(linhas: list[str]) -> tuple[str, str, list[str]]:
    """Extrai id/título das linhas de cabeçalho (# ...) e devolve o corpo."""
    numero = ""
    titulo = ""
    corpo: list[str] = []
    for linha in linhas:
        if linha.startswith("#"):
            texto = linha.lstrip("# ").strip()
            if texto.lower().startswith("título"):
                titulo = texto.split(":", 1)[1].strip() if ":" in texto else texto
            elif not numero:
                numero = texto
            continue
        corpo.append(linha)
    return numero, titulo, corpo


async def _ingestir_arquivos(diretorio: Path, prefixo_id: str, nome_fonte: str) -> int:
    if not diretorio.exists():
        logger.warning("Diretório não encontrado: %s", diretorio)
        return 0

    total = 0
    async with async_session_factory() as db:
        for file_path in sorted(diretorio.glob("*.txt")):
            linhas = file_path.read_text(encoding="utf-8").splitlines()
            numero, titulo, corpo = _ler_metadata(linhas)
            if not numero:
                numero = f"{prefixo_id} {file_path.stem}"
            if not titulo:
                titulo = file_path.stem

            try:
                await ingest_extra_document(
                    db,
                    content="\n".join(corpo),
                    law_number=numero,
                    law_title=titulo,
                    source_url="corpus local",
                    version=nome_fonte,
                )
                total += 1
            except ValueError as e:
                logger.warning("Arquivo sem conteúdo ignorado: %s (%s)", file_path.name, e)

        await build_fts_index(db)
        await db.commit()
    logger.info("Fonte %s: %d documentos ingeridos", nome_fonte, total)
    return total


async def main() -> int:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    total = 0
    for fonte in FONTES:
        total += await _ingestir_arquivos(
            DATA_DIR / fonte["diretorio"],
            fonte["prefixo_id"],
            fonte["nome"],
        )
    logger.info("Ingestão de corpus extra concluída: %d documentos", total)
    return total


if __name__ == "__main__":
    asyncio.run(main())
