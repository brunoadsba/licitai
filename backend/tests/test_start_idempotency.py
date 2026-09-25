"""Duplo POST /analysis/{id}/start — serialização via with_for_update.

Segundo start com análise pendente → 202 com o mesmo analysis_id
(re-enfileira, não duplica). Com análise running → 409.
"""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis
from app.models.document import Document

_ENGINES: list = []


def _run(coroutine):
    return asyncio.run(coroutine)


async def _montar_doc(Session) -> uuid.UUID:
    async with Session() as session:
        doc = Document(
            filename_original="TR-dup.pdf",
            filename_stored="tr-dup.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="parsed",
            classification="publico",
            total_items=0,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc.id


def _novo_session() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _ENGINES.append(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_init())
    return async_sessionmaker(engine, expire_on_commit=False)


async def _post_start(Session, document_id: uuid.UUID):
    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/analysis/{document_id}/start",
                headers={"X-Document-Classification": "publico"},
                json={"mode": "economic"},
            )
            return {"status_code": resp.status_code, "json": resp.json()}
    finally:
        app.dependency_overrides.clear()


def _dispose():
    for _engine in _ENGINES:
        asyncio.run(_engine.dispose())
    _ENGINES.clear()


def test_segundo_start_pendente_reenfileira_mesma_analise():
    Session = _novo_session()
    try:
        doc_id = _run(_montar_doc(Session))
        primeiro = _run(_post_start(Session, doc_id))
        assert primeiro["status_code"] == 202
        segundo = _run(_post_start(Session, doc_id))
        assert segundo["status_code"] == 202
        assert segundo["json"]["analysis_id"] == primeiro["json"]["analysis_id"]
    finally:
        _dispose()


def test_start_com_running_retorna_409():
    Session = _novo_session()
    try:
        doc_id = _run(_montar_doc(Session))

        async def _marcar_running():
            async with Session() as session:
                session.add(
                    Analysis(
                        document_id=doc_id,
                        status="running",
                        llm_provider="groq",
                        llm_model="test",
                        analysis_mode="economic",
                        total_items=0,
                        analyzed_items=0,
                    )
                )
                await session.commit()

        _run(_marcar_running())
        result = _run(_post_start(Session, doc_id))
        assert result["status_code"] == 409
    finally:
        _dispose()
