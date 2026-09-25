"""GET /readyz — divergência de schema_version → 503."""

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.config import settings
from app.main import app

_ENGINES: list = []


def _run(coroutine):
    return asyncio.run(coroutine)


def _engine_com_schema(version: str):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _ENGINES.append(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT)")
            )
            await conn.execute(
                text(
                    "INSERT INTO schema_meta (key, value) "
                    "VALUES ('schema_version', :v)"
                ),
                {"v": version},
            )

    _run(_init())
    return engine


def _get_readyz(monkeypatch, engine) -> dict:
    monkeypatch.setattr(main_module, "engine", engine)
    try:

        async def _call():
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as ac:
                resp = await ac.get("/readyz")
                return {"status_code": resp.status_code, "json": resp.json()}

        return _run(_call())
    finally:
        for _engine in _ENGINES:
            asyncio.run(_engine.dispose())
        _ENGINES.clear()


def test_readyz_schema_divergente_retorna_503(monkeypatch):
    engine = _engine_com_schema("versao-antiga-qualquer")
    result = _get_readyz(monkeypatch, engine)
    assert result["status_code"] == 503
    assert result["json"]["status"] == "not_ready"
    assert "mismatch" in result["json"]["checks"]["schema"]


def test_readyz_schema_compativel_retorna_200(monkeypatch):
    engine = _engine_com_schema(settings.expected_schema_version)
    result = _get_readyz(monkeypatch, engine)
    assert result["status_code"] == 200
    assert result["json"]["status"] == "ready"
