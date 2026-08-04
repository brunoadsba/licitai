"""
Testes de integração do endpoint POST /documents/diff (RAG Fase 4.3).

Usa banco SQLite em memória com dois documentos TR e itens, validando os
guards (404/400) e o formato da resposta.
"""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.document import Document, DocumentItem


async def _montar_cenario() -> tuple[async_sessionmaker, dict]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        antigo = Document(
            filename_original="TR-antigo.pdf",
            filename_stored="tr-antigo.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="parsed",
        )
        novo = Document(
            filename_original="TR-novo.pdf",
            filename_stored="tr-novo.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="parsed",
        )
        session.add_all([antigo, novo])
        await session.commit()
        await session.refresh(antigo)
        await session.refresh(novo)

        session.add_all([
            DocumentItem(document_id=antigo.id, item_number="1", title="Objeto",
                         content="Contratação de serviços de limpeza.", item_order=0),
            DocumentItem(document_id=antigo.id, item_number="2", title="Vigência",
                         content="Vigência de 12 meses.", item_order=1),
            DocumentItem(document_id=novo.id, item_number="1", title="Objeto",
                         content="Contratação de serviços de limpeza e conservação.", item_order=0),
            DocumentItem(document_id=novo.id, item_number="3", title="Garantia",
                         content="Exigida garantia de 5%.", item_order=2),
        ])
        await session.commit()

        ids = {"antigo": antigo.id, "novo": novo.id}
    return Session, ids


def _run(coroutine):
    return asyncio.run(coroutine)


async def _post_diff(Session, body: dict) -> dict:
    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/v1/documents/diff", json=body)
            return {
                "status": response.status_code,
                "body": response.json() if response.content else {},
            }
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_diff_endpoint_ok():
    async def _cenario():
        Session, ids = await _montar_cenario()
        return await _post_diff(Session, {
            "documento_antigo_id": str(ids["antigo"]),
            "documento_novo_id": str(ids["novo"]),
        })

    resultado = _run(_cenario())

    assert resultado["status"] == 200
    body = resultado["body"]
    assert body["total"] == 3
    assert body["resumo"]["adicionado"] == 1
    assert body["resumo"]["removido"] == 1
    statuses = {item["item_number"]: item["status"] for item in body["itens"]}
    assert statuses["1"] == "inalterado"
    assert statuses["2"] == "removido"
    assert statuses["3"] == "adicionado"


def test_diff_endpoint_404_documento_inexistente():
    async def _cenario():
        Session, ids = await _montar_cenario()
        return await _post_diff(Session, {
            "documento_antigo_id": str(uuid.uuid4()),
            "documento_novo_id": str(ids["novo"]),
        })

    resultado = _run(_cenario())
    assert resultado["status"] == 404
