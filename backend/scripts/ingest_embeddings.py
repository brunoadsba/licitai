"""
Script de ingestão de embeddings semânticos para os chunks do corpus jurídico (RAG Fase 4.1).

Gera vetores de embeddings usando o EmbeddingsProvider configurado (Gemini ou Ollama)
e persiste na coluna `legal_chunks.embedding` em formato JSON.

Uso:
    $env:PYTHONPATH="backend"
    backend\.venv\Scripts\python.exe backend\scripts\ingest_embeddings.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Adicionar pasta backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session_factory
from app.models.legal import LegalChunk
from app.services.embeddings import get_embeddings_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ingest_embeddings")


async def run_embeddings_ingestion():
    logger.info("Iniciando ingestão de embeddings semânticos...")

    try:
        provider = get_embeddings_provider()
        logger.info("Provedor de Embeddings ativo: %s (%s)", provider.provider_name, provider.model_name)
    except Exception as e:
        logger.error("Erro ao obter provedor de embeddings: %s", e)
        return

    async with async_session_factory() as db:
        # Carregar chunks pendentes
        result = await db.execute(
            select(LegalChunk).where(LegalChunk.embedding.isnot(None) == False)  # noqa: E712
        )
        chunks = result.scalars().all()

        total = len(chunks)
        if total == 0:
            logger.info("Todos os chunks já possuem embeddings. Nenhuma ação necessária.")
            return

        logger.info("Encontrados %d chunks pendentes de embedding.", total)

        processed = 0
        failed = 0

        for idx, chunk in enumerate(chunks, start=1):
            try:
                # Gerar vetor de embedding
                vector = await provider.embed(chunk.chunk_text)
                chunk.embedding = json.dumps(vector)
                processed += 1

                if idx % 10 == 0 or idx == total:
                    await db.commit()
                    logger.info("Progresso: %d/%d chunks processados", idx, total)

            except Exception as e:
                failed += 1
                logger.warning("Falha ao gerar embedding para chunk %s: %s", chunk.id, e)
                # Tentar continuar com os demais

        await db.commit()
        logger.info(
            "Ingestão concluída: %d processados com sucesso, %d falhas.",
            processed,
            failed,
        )


if __name__ == "__main__":
    asyncio.run(run_embeddings_ingestion())
