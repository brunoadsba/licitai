"""Modelo jurídico versionado: hierarquia, vigência e mapeamento."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal_versioned import LegalIdMap, LegalProvision, LegalVersion, LegalWork
from app.services.ingest.hashing import sha256_text
from app.services.ingest.pipeline import ingest_legal_source
from app.services.legal_model.migrate import migrate_sample
from app.services.legal_model.persist import upsert_versioned_work
from app.services.legal_model.provisions import parse_provisions
from app.services.legal_model.query import ancestors_and_related, list_provisions

LAW = (
    "Art. 1º Caput do primeiro.\n"
    "§ 1º Parágrafo especial.\n"
    "I - inciso um;\n"
    "II - inciso dois;\n"
    "Art. 2º (VETADO)\n"
    "Art. 3º Texto vigente ~~antigo~~ final.\n"
)


def _engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_parser_hierarquico_e_vetado():
    drafts = parse_provisions(LAW)
    paths = [d.path for d in drafts]
    assert "art.1" in paths
    assert "art.1/par.1º" in paths or "art.1/par.1" in paths
    assert any(p.endswith("/inc.I") for p in paths)
    assert any(p.endswith("/inc.II") for p in paths)
    assert "art.2" not in paths
    art3 = next(d for d in drafts if d.path == "art.3")
    assert "antigo" not in art3.canonical_text
    assert "final" in art3.canonical_text


def test_ingest_dupla_escrita_e_consulta_vigente():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            first = await ingest_legal_source(
                db,
                content=LAW,
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://www.planalto.gov.br/l14133",
                origin="planalto",
            )
            second = await ingest_legal_source(
                db,
                content=LAW,
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://www.planalto.gov.br/l14133",
                origin="planalto",
            )
            vigente = await list_provisions(db, law_number="Lei 14.133/2021")
            historico = await list_provisions(
                db, law_number="Lei 14.133/2021", include_historical=True
            )
            works = (await db.execute(select(LegalWork))).scalars().all()
            versions = (await db.execute(select(LegalVersion))).scalars().all()
            child = next(p for p in vigente if p.inciso == "I")
            chain = await ancestors_and_related(db, child)
            return first, second, vigente, historico, works, versions, chain

    first, second, vigente, historico, works, versions, chain = asyncio.run(_run())
    assert first.success and second.unchanged
    assert len(works) == 1
    assert len(versions) == 1
    assert all(p.status == "vigente" for p in vigente)
    assert not any(p.path.startswith("art.2") for p in vigente)
    assert len(historico) >= len(vigente)
    assert [p.path for p in chain][0].startswith("art.1")
    assert chain[-1].inciso == "I"


def test_nova_versao_imuta_anterior_e_um_vigente_por_path():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            v1 = await upsert_versioned_work(
                db,
                content="Art. 1º Texto A.\n",
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://exemplo",
                collected_at=None,
                content_hash=sha256_text("A"),
            )
            v2 = await upsert_versioned_work(
                db,
                content="Art. 1º Texto B.\n",
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url="https://exemplo",
                collected_at=None,
                content_hash=sha256_text("B"),
            )
            await db.commit()
            await db.refresh(v1)
            vigente = await list_provisions(db, law_number="Lei 14.133/2021")
            historico = await list_provisions(
                db, law_number="Lei 14.133/2021", include_historical=True
            )
            return v1.status, v2.status, vigente, historico

    old_status, new_status, vigente, historico = asyncio.run(_run())
    assert old_status == "superseded"
    assert new_status == "published"
    assert len(vigente) == 1
    assert vigente[0].canonical_text.startswith("Art. 1º Texto B")
    assert sum(1 for p in historico if p.path == "art.1") == 2


def test_tcu_nao_publica_sem_fonte_validada():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            version = await upsert_versioned_work(
                db,
                content="Art. 1º Enunciado da súmula.\n",
                law_number="Súmula 247/TCU",
                law_title="Parcelamento",
                source_url="https://pesquisa.apps.tcu.gov.br/",
                collected_at=None,
                content_hash=sha256_text("tcu"),
                source_version="quarantine-0B",
            )
            vigente = await list_provisions(db, law_number="Súmula 247/TCU")
            return version.status, vigente

    status, vigente = asyncio.run(_run())
    assert status == "unpublished"
    assert vigente == []


def test_migracao_amostra_mapeia_chunk():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            await ingest_legal_source(
                db,
                content="Art. 6º O objeto da licitação.\nArt. 11. O edital.\n",
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                origin="planalto",
            )
            reports = await migrate_sample(db, ("Lei 14.133/2021",))
            maps = (await db.execute(select(LegalIdMap))).scalars().all()
            return reports[0], maps

    report, maps = asyncio.run(_run())
    assert report.old_chunks == 2
    assert report.mapped == 2
    assert report.missing_articles == []
    assert len(maps) == 2


def test_dois_vigentes_no_mesmo_path_falham():
    async def _run():
        engine = _engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            await upsert_versioned_work(
                db,
                content="Art. 1º Um.\n",
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                source_url=None,
                collected_at=None,
                content_hash=sha256_text("1"),
            )
            work = (await db.execute(select(LegalWork))).scalar_one()
            version = (await db.execute(select(LegalVersion))).scalar_one()
            db.add(
                LegalProvision(
                    version_id=version.id,
                    work_id=work.id,
                    path="art.1",
                    article="Art. 1º",
                    canonical_text="duplicado",
                    status="vigente",
                    provision_hash=sha256_text("dup"),
                )
            )
            await db.flush()

    with pytest.raises(Exception):
        asyncio.run(_run())
