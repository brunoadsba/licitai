"""
Testes da ingestão de corpus extra (RAG Fase 4.2).

Cobre o chunker genérico (`parse_extra_text`) para documentos sem estrutura
de "Art." (acórdãos TCU, instruções RILC) e a persistência idempotente via
`ingest_extra_document`.
"""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.loader import parse_extra_text, ingest_extra_document


def test_parse_extra_text_ignora_cabecalho():
    conteudo = (
        "# Acórdão 1234/2024\n"
        "# Título: Prestação de contas\n"
        "Primeiro parágrafo do acórdão.\n"
        "Segundo parágrafo com mais conteúdo.\n"
    )
    chunks = parse_extra_text(conteudo)

    assert len(chunks) >= 1
    assert "Acórdão 1234/2024" not in chunks[0].text
    assert "Prestação de contas" not in chunks[0].text
    assert "Primeiro parágrafo" in chunks[0].text


def test_parse_extra_text_agrupa_ate_limite():
    conteudo = "\n".join(f"parágrafo {i} com conteúdo razoável" for i in range(40))
    chunks = parse_extra_text(conteudo, chunk_chars=150)

    assert len(chunks) > 1
    # Nenhum chunk ultrapassa o limite por uma margem significativa
    assert all(len(c.text) <= 220 for c in chunks)
    # Ordena os trechos sequencialmente
    assert chunks[0].article == "Trecho 1"
    assert chunks[1].article == "Trecho 2"


def test_parse_extra_text_corta_na_marca_do_dou():
    conteudo = "Texto do acórdão.\nEste texto não substitui o publicado no DOU\nignorado"
    chunks = parse_extra_text(conteudo)
    assert "ignorado" not in "".join(c.text for c in chunks)


def test_ingest_extra_document_persiste(monkeypatch):
    async def _cenario():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            doc = await ingest_extra_document(
                db,
                content=(
                    "# Acórdão 500/2024\n"
                    "Decidiu o Tribunal pela irregularidade das contas.\n"
                    "Determinações ao gestor responsável.\n"
                ),
                law_number="Acórdão 500/2024",
                law_title="Prestação de contas TCU",
            )
            await db.commit()
            chunks = (await db.execute(
                select(LegalChunk).where(LegalChunk.legal_document_id == doc.id)
            )).scalars().all()
            return len(chunks), doc.total_chunks

    total, previsto = asyncio.run(_cenario())
    assert total == previsto == 1


def test_ingest_extra_document_idempotente(monkeypatch):
    async def _cenario():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            conteudo = "# Acórdão 700/2024\nConteúdo único.\n"
            await ingest_extra_document(
                db, conteudo, "Acórdão 700/2024", "Título"
            )
            await ingest_extra_document(
                db, conteudo, "Acórdão 700/2024", "Título"
            )
            await db.commit()
            docs = (await db.execute(select(LegalDocument))).scalars().all()
            chunks = (await db.execute(select(LegalChunk))).scalars().all()
            return len(docs), len(chunks)

    docs, chunks = asyncio.run(_cenario())
    assert docs == 1
    assert chunks == 1


def test_ingest_extra_document_vazio_sobe_erro():
    async def _cenario():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            with pytest.raises(ValueError):
                await ingest_extra_document(
                    db, content="", law_number="Vazio", law_title="Sem conteúdo"
                )

    asyncio.run(_cenario())
