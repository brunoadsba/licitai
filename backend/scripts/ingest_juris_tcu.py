"""
Script de Ingestão de Jurisprudência Relevante do TCU (RAG Fase 4.2).

Popula legal_documents/legal_chunks com súmulas/acórdãos do TCU.

O RILC CODEBA completo é ingerido separadamente:
    PYTHONPATH=. python scripts/ingest_rilc_codeba.py

Uso:
    PYTHONPATH=. python scripts/ingest_juris_tcu.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_factory, engine, Base
from app.services.rag.loader import ingest_extra_document, build_fts_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ingest_juris_tcu")

JURISPRUDENCIA_DATA = [
    {
        "law_number": "Súmula 247/TCU",
        "law_title": "Princípio do Parcelamento do Objeto e Competitividade",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Súmula TCU",
        "content": """SÚMULA Nº 247 DO TCU:
É obrigatória a admissão da adjudicação por item e não por lote, nas licitações para a contratação de obras, serviços, compras e alienações, cujo objeto seja divisível, desde que não haja prejuízo para o conjunto ou perda de economia de escala, tendo em vista o objetivo de propiciar a ampla participação de licitantes que, embora não dispondo de capacidade para a execução da totalidade do objeto, possam fazê-lo com relação a itens isolados.
Art. 47, II da Lei 14.133/2021 estabelece que as licitações atenderão ao princípio do parcelamento quando for tecnicamente viável e economicamente vantajoso.""",
    },
    {
        "law_number": "Súmula 272/TCU",
        "law_title": "Votação de Marcas e Especificações Exclusivas",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Súmula TCU",
        "content": """SÚMULA Nº 272 DO TCU:
No edital de licitação, é vedada a indicação de marca, característica ou especificação exclusiva, salvo nos casos formalmente justificados no processo administrativo de contratação pela autoridade competente.
Art. 41, I da Lei 14.133/2021 autoriza indicação de marca apenas para padronização, padronização técnica previamente formalizada ou quando for a única capaz de atender às necessidades da Administração.""",
    },
    {
        "law_number": "Acórdão 1214/2013-TCU-Plenário",
        "law_title": "Critérios de Qualificação Técnica e Exequibilidade",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Acórdão TCU",
        "content": """ACÓRDÃO 1214/2013 PLENÁRIO TCU:
A exigência de quantitativos mínimos em atestados de capacidade técnico-operacional não deve ultrapassar 50% dos quantitativos previstos para o objeto da licitação, salvo em casos excepcionais devidamente justificados no Termo de Referência. Exigências desproporcionais restringem indevidamente o caráter competitivo da licitação.""",
    },
]


async def run_jurisprudencia_ingestion():
    logger.info("Iniciando ingestão de Jurisprudência TCU...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        for item in JURISPRUDENCIA_DATA:
            logger.info("Ingerindo documento: %s (%s)", item["law_number"], item["law_title"])
            await ingest_extra_document(
                db,
                content=item["content"],
                law_number=item["law_number"],
                law_title=item["law_title"],
                source_url=item["source_url"],
                version=item["version"],
            )

        logger.info("Reconstruindo índice de busca FTS...")
        await build_fts_index(db)

        await db.commit()

    logger.info("Ingestão de Jurisprudência TCU concluída com sucesso!")


if __name__ == "__main__":
    asyncio.run(run_jurisprudencia_ingestion())
