"""Fase 0B: fontes TCU não verificadas saem da busca e do fundamento."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.services.analyzer.grounding import get_valid_legal_refs
from app.services.rag.loader import build_fts_index
from app.services.rag.quarantine import (
    QUARANTINE_ONLY_MESSAGE,
    QUARANTINE_VERSION,
    consume_quarantine_only,
    sanitize_legal_basis,
    scrub_quarantined_text,
)
from app.services.rag.retriever import _clear_legal_context_cache, retrieve


def _run(coro):
    return asyncio.run(coro)


async def _seed() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        lei = LegalDocument(
            law_number="Lei 14.133/2021",
            law_title="Licitações",
            version="oficial",
        )
        tcu = LegalDocument(
            law_number="Súmula 247/TCU",
            law_title="Parcelamento",
            version=QUARANTINE_VERSION,
            source_url="https://pesquisa.apps.tcu.gov.br/",
        )
        db.add_all([lei, tcu])
        await db.flush()
        db.add_all(
            [
                LegalChunk(
                    legal_document_id=lei.id,
                    chunk_index=0,
                    article="Art. 47",
                    chunk_text=(
                        "As licitações atenderão ao princípio do parcelamento "
                        "quando for tecnicamente viável."
                    ),
                ),
                LegalChunk(
                    legal_document_id=tcu.id,
                    chunk_index=0,
                    article="Súmula 247",
                    chunk_text=(
                        "É obrigatória a admissão da adjudicação por item "
                        "e não por lote para ampla competitividade."
                    ),
                ),
            ]
        )
        await build_fts_index(db)
        await db.commit()
    return Session


def test_retrieve_exclui_sumula_tcu_e_mantem_lei():
    async def _cenario():
        _clear_legal_context_cache()
        Session = await _seed()
        async with Session() as db:
            chunks = await retrieve(db, "parcelamento adjudicação por item", top_k=5)
            laws = {c.law_number for c in chunks}
            assert "Súmula 247/TCU" not in laws
            assert "Lei 14.133/2021" in laws
            assert consume_quarantine_only() is False

    _run(_cenario())


def test_retrieve_so_tcu_informa_ausencia():
    async def _cenario():
        _clear_legal_context_cache()
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            tcu = LegalDocument(
                law_number="Acórdão 1214/2013-TCU-Plenário",
                law_title="Qualificação",
                version=QUARANTINE_VERSION,
            )
            db.add(tcu)
            await db.flush()
            db.add(
                LegalChunk(
                    legal_document_id=tcu.id,
                    chunk_index=0,
                    article="ementa",
                    chunk_text=(
                        "quantitativos mínimos em atestados de capacidade "
                        "técnico-operacional não devem ultrapassar 50%"
                    ),
                )
            )
            await build_fts_index(db)
            await db.commit()
            chunks = await retrieve(db, "quantitativos mínimos atestados 50%", top_k=5)
            assert chunks == []
            assert consume_quarantine_only() is True
        assert "quarentena" in QUARANTINE_ONLY_MESSAGE.lower()

    _run(_cenario())


@pytest.mark.asyncio
async def test_valid_refs_ignoram_tcu_quarentena():
    Session = await _seed()
    async with Session() as db:
        refs = await get_valid_legal_refs(db)
    blob = " ".join(refs).lower()
    assert "247" not in blob
    assert any("14.133" in r for r in refs)


def test_sanitize_legal_basis_e_parecer():
    assert sanitize_legal_basis("Súmula 247/TCU, parcelamento") is None
    assert sanitize_legal_basis("Acórdão 1214/2013-TCU-Plenário") is None
    assert sanitize_legal_basis("Art. 47 da Lei 14.133/2021") is not None
    parecer = (
        "O item viola a Súmula 247 do TCU. O Art. 47 da Lei 14.133/2021 "
        "já trata do parcelamento."
    )
    limpo = scrub_quarantined_text(parecer)
    assert limpo is not None
    assert "247" not in limpo
    assert "14.133" in limpo
