"""Guarda: análise só para document_type=tr."""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.comparison import Fornecedor
from app.models.document import Document


async def _setup():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        forn = Fornecedor(nome="Guard Forn")
        session.add(forn)
        await session.commit()
        await session.refresh(forn)
        doc = Document(
            filename_original="prop.docx",
            filename_stored="prop.docx",
            file_type="docx",
            file_size_bytes=100,
            document_type="proposta",
            fornecedor_id=forn.id,
            status="parsed",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        ids = {"doc": doc.id, "forn": forn.id}

    async def override_get_db():
        async with Session() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    return engine, ids


def test_start_analysis_rejects_proposta():
    async def _run():
        engine, ids = await _setup()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/analysis/{ids['doc']}/start",
                    json={"mode": "economic"},
                )
                assert resp.status_code == 400
                assert "Termos de Referência" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()
            await engine.dispose()

    asyncio.run(_run())
