"""Regressão auditoria 15/09: claim concorrente só entrega 1x (SQLite)."""

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.job import Job  # noqa: F401 — registra metadata
from app.database import Base
from app.services.jobs import queue


@pytest_asyncio.fixture
async def two_sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_claim_concorrente_so_um_vence(two_sessions):
    async with two_sessions() as db:
        job = await queue.enqueue(db, "analysis", {"a": "1"})
        await db.commit()
        job_id = job.id

    async def _claim_one():
        async with two_sessions() as db:
            claimed = await queue.claim(db)
            await db.commit()
            return claimed.id if claimed else None

    r1, r2 = await asyncio.gather(_claim_one(), _claim_one())
    vencedores = [r for r in (r1, r2) if r is not None]
    assert len(vencedores) == 1
    assert vencedores[0] == job_id


@pytest.mark.asyncio
async def test_claim_by_id_duplo_so_um_vence(two_sessions):
    async with two_sessions() as db:
        job = await queue.enqueue(db, "analysis", {"a": "1"})
        await db.commit()
        job_id = job.id

    async def _claim_id():
        async with two_sessions() as db:
            claimed = await queue.claim_by_id(db, job_id)
            await db.commit()
            return claimed is not None

    r = await asyncio.gather(_claim_id(), _claim_id())
    assert sum(1 for x in r if x) == 1
