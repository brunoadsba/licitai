"""
Script de Ingestão de Jurisprudência Relevante do TCU e RILC CODEBA (RAG Fase 4.2).

Popula as tabelas legal_documents e legal_chunks com entendimentos consolidados
do Tribunal de Contas da União e do Regulamento Interno de Licitações.

Uso:
    $env:PYTHONPATH="backend"
    backend\.venv\Scripts\python.exe backend\scripts\ingest_juris_tcu.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adicionar pasta backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_factory, engine, Base
from app.services.rag.loader import ingest_law_text, ingest_extra_document, build_fts_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ingest_juris_tcu")

JURISPRUDENCIA_DATA = [
    {
        "law_number": "Súmula 247/TCU",
        "law_title": "Princípio do Parcelamento do Objeto e Competitividade",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Súmula TCU",
        "is_law": False,
        "content": """SÚMULA Nº 247 DO TCU:
É obrigatória a admissão da adjudicação por item e não por lote, nas licitações para a contratação de obras, serviços, compras e alienações, cujo objeto seja divisível, desde que não haja prejuízo para o conjunto ou perda de economia de escala, tendo em vista o objetivo de propiciar a ampla participação de licitantes que, embora não dispondo de capacidade para a execução da totalidade do objeto, possam fazê-lo com relação a itens isolados.
Art. 47, II da Lei 14.133/2021 estabelece que as licitações atenderão ao princípio do parcelamento quando for tecnicamente viável e economicamente vantajoso.""",
    },
    {
        "law_number": "Súmula 272/TCU",
        "law_title": "Votação de Marcas e Especificações Exclusivas",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Súmula TCU",
        "is_law": False,
        "content": """SÚMULA Nº 272 DO TCU:
No edital de licitação, é vedada a indicação de marca, característica ou especificação exclusiva, salvo nos casos formalmente justificados no processo administrativo de contratação pela autoridade competente.
Art. 41, I da Lei 14.133/2021 autoriza indicação de marca apenas para padronização, padronização técnica previamente formalizada ou quando for a única capaz de atender às necessidades da Administração.""",
    },
    {
        "law_number": "Acórdão 1214/2013-TCU-Plenário",
        "law_title": "Critérios de Qualificação Técnica e Exequibilidade",
        "source_url": "https://pesquisa.apps.tcu.gov.br/",
        "version": "Acórdão TCU",
        "is_law": False,
        "content": """ACÓRDÃO 1214/2013 PLENÁRIO TCU:
A exigência de quantitativos mínimos em atestados de capacidade técnico-operacional não deve ultrapassar 50% dos quantitativos previstos para o objeto da licitação, salvo em casos excepcionais devidamente justificados no Termo de Referência. Exigências desproporcionais restringem indevidamente o caráter competitivo da licitação.""",
    },
    {
        "law_number": "RILC-CODEBA-2023",
        "law_title": "Regulamento Interno de Licitações e Contratos da CODEBA",
        "source_url": "https://www.codeba.gov.br/",
        "version": "RILC V1.2",
        "is_law": True,
        "content": """REGULAMENTO INTERNO DE LICITAÇÕES E CONTRATOS - CODEBA:

Art. 15. O Termo de Referência ou Projeto Básico é o documento necessário para a contratação de bens e serviços na CODEBA, devendo conter obrigatoriamente:
I - Definição clara, precisa e suficiente do objeto;
II - Justificativa da necessidade da contratação sob a perspectiva do interesse público e portuário;
III - Especificações técnicas detalhadas, vedadas especificações direcionadas;
IV - Prazos de execução, entrega, garantia e cronograma de medições;
V - Critérios objetivos de medição e recebimento dos bens ou serviços;
VI - Matriz de riscos quando a complexidade do objeto recomendar;
VII - Estimativa do valor da contratação acompanhada da composição de preços unitários.

Art. 38. A gestão e fiscalização dos contratos serão exercidas por empregado especialmente designado pela Diretoria da CODEBA.""",
    },
]


async def run_jurisprudencia_ingestion():
    logger.info("Iniciando ingestão de Jurisprudência TCU e RILC CODEBA...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        for item in JURISPRUDENCIA_DATA:
            logger.info("Ingerindo documento: %s (%s)", item["law_number"], item["law_title"])
            if item.get("is_law"):
                await ingest_law_text(
                    db,
                    content=item["content"],
                    law_number=item["law_number"],
                    law_title=item["law_title"],
                    source_url=item["source_url"],
                    version=item["version"],
                )
            else:
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

    logger.info("Ingestão de Jurisprudência concluída com sucesso!")


if __name__ == "__main__":
    asyncio.run(run_jurisprudencia_ingestion())
