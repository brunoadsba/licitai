"""
Script de seed de moldes de regras padrão (RF02).

Insere no banco os moldes base do módulo de auditoria TR × Propostas,
caso ainda não existam (idempotente por nome).

Uso:
    python scripts/seed_moldes.py
"""

import asyncio
import json
import logging

from sqlalchemy import select

from app.database import engine, async_session_factory, Base
from app.models.comparison import Molde  # noqa: F401
from app.services.rules.loader import parse_molde

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MOLDES = [
    {
        "nome": "Molde Padrão de TR",
        "descricao": (
            "Regras básicas de conformidade para termos de referência: "
            "vigência, garantia e base legal."
        ),
        "config_json": {
            "versao": 1,
            "regras": [
                {
                    "id": "vigencia_dias",
                    "rotulo": "Vigência mínima",
                    "tipo": "numero_inteiro",
                    "ancora": "vigência",
                    "unidade": "dias",
                },
                {
                    "id": "garantia_exigida",
                    "rotulo": "Garantia exigida",
                    "tipo": "booleano",
                    "ancora": "garantia",
                    "palavras_chave": ["garantia", "caução"],
                },
                {
                    "id": "lei_14133",
                    "rotulo": "Lei 14.133/2021 citada",
                    "tipo": "legal",
                    "ancora": "lei",
                    "regex": r"14\.133/2021",
                },
            ],
        },
    },
    {
        "nome": "Molde de Serviços Continuados",
        "descricao": (
            "Regras para contratos de serviços com dedicação exclusiva de "
            "mão de obra: vigência, pagamento e reajuste."
        ),
        "config_json": {
            "versao": 1,
            "regras": [
                {
                    "id": "vigencia_meses",
                    "rotulo": "Vigência do contrato",
                    "tipo": "numero_inteiro",
                    "ancora": "vigência",
                    "unidade": "meses",
                },
                {
                    "id": "prazo_pagamento",
                    "rotulo": "Prazo de pagamento",
                    "tipo": "numero_inteiro",
                    "ancora": "pagamento",
                    "unidade": "dias",
                },
                {
                    "id": "reajuste_percentual",
                    "rotulo": "Reajuste anual",
                    "tipo": "percentual",
                    "ancora": "reajuste",
                    "unidade": "%",
                },
                {
                    "id": "garantia_obrigatoria",
                    "rotulo": "Garantia contratual",
                    "tipo": "booleano",
                    "ancora": "garantia",
                    "palavras_chave": ["garantia", "caução"],
                },
            ],
        },
    },
    {
        "nome": "Molde de Obras Públicas",
        "descricao": (
            "Regras para TR de obras: valor estimado, prazo, cronograma "
            "físico-financeiro e base legal."
        ),
        "config_json": {
            "versao": 1,
            "regras": [
                {
                    "id": "valor_estimado",
                    "rotulo": "Valor estimado da obra",
                    "tipo": "monetario",
                    "ancora": "valor estimado",
                },
                {
                    "id": "prazo_execucao",
                    "rotulo": "Prazo de execução",
                    "tipo": "numero_inteiro",
                    "ancora": "prazo",
                    "unidade": "dias",
                },
                {
                    "id": "data_entrega",
                    "rotulo": "Data de entrega",
                    "tipo": "data",
                    "ancora": "entrega",
                },
                {
                    "id": "cronograma",
                    "rotulo": "Cronograma físico-financeiro",
                    "tipo": "booleano",
                    "ancora": "cronograma",
                    "palavras_chave": ["cronograma"],
                },
            ],
        },
    },
]


async def main() -> None:
    """Cria as tabelas e insere os moldes padrão (idempotente)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        for item in MOLDES:
            resultado = await db.execute(
                select(Molde).where(Molde.nome == item["nome"])
            )
            if resultado.scalar_one_or_none():
                logger.info("Molde já existe, ignorando: %s", item["nome"])
                continue

            config_json = json.dumps(item["config_json"], ensure_ascii=False)
            # Valida antes de persistir (garante integridade do seed)
            parse_molde(config_json)

            db.add(Molde(
                nome=item["nome"],
                descricao=item["descricao"],
                config_json=config_json,
            ))
            await db.flush()
            logger.info("Molde criado: %s", item["nome"])

        await db.commit()

    logger.info("Seed de moldes concluído.")


if __name__ == "__main__":
    asyncio.run(main())
