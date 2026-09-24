"""Inventário de fontes do piloto."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalDocument
from app.models.legal_versioned import LegalWork
from app.services.legal_model.catalog import list_pilot_sources


def test_list_pilot_sources_marca_ingerido_e_tcu_ausente():
    async def _run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            db.add(LegalWork(law_number="Lei 14.133/2021", title="LLCA", kind="lei"))
            await db.commit()
            rows = await list_pilot_sources(db)

        by_id = {r["id"]: r for r in rows}
        assert by_id["Lei 14.133/2021"]["status"] == "em_uso"
        assert by_id["Lei 14.133/2021"]["searchable"] is True
        assert by_id["Lei 13.303/2016"]["status"] == "nao_ingerido"
        assert by_id["Lei 13.303/2016"]["searchable"] is False
        assert by_id["RILC CODEBA"]["searchable"] is False
        assert by_id["tcu"]["status"] == "nao_ingerido"
        assert by_id["tcu"]["searchable"] is False
        await engine.dispose()

    asyncio.run(_run())


def test_list_pilot_sources_rilc_e_tcu_via_legal_documents():
    async def _run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            db.add(
                LegalDocument(
                    law_number="RILC-CODEBA",
                    law_title="Regulamento Interno de Licitações e Contratos da CODEBA",
                )
            )
            db.add(
                LegalDocument(
                    law_number="Súmula 247/TCU",
                    law_title="Princípio do Parcelamento",
                )
            )
            await db.commit()
            rows = await list_pilot_sources(db)

        by_id = {r["id"]: r for r in rows}
        assert by_id["RILC CODEBA"]["status"] == "em_uso"
        assert by_id["RILC CODEBA"]["searchable"] is True
        assert by_id["RILC CODEBA"]["search_law"] == "RILC"
        assert by_id["tcu"]["status"] == "quarentena"
        assert by_id["tcu"]["searchable"] is False
        await engine.dispose()

    asyncio.run(_run())
