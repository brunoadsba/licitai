"""Testes da fila durável de jobs."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.job import Job  # noqa: F401
from app.services.jobs.queue import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    claim,
    complete,
    enqueue,
    fail,
    reclaim_expired,
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_enqueue_claim_complete(db_session: AsyncSession):
    job = await enqueue(db_session, "analysis", {"analysis_id": str(uuid.uuid4())})
    await db_session.commit()
    assert job.status == STATUS_PENDING

    claimed = await claim(db_session)
    await db_session.commit()
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == STATUS_RUNNING
    assert claimed.attempts == 1

    await complete(db_session, claimed.id, result={"ok": True})
    await db_session.commit()
    await db_session.refresh(claimed)
    assert claimed.status == STATUS_COMPLETED


@pytest.mark.asyncio
async def test_reclaim_expired_returns_to_pending(db_session: AsyncSession):
    job = await enqueue(db_session, "comparacao", {"comparacao_id": "x"}, max_attempts=3)
    await db_session.commit()
    claimed = await claim(db_session, lease_seconds=1)
    assert claimed is not None
    claimed.lease_until = datetime.now(timezone.utc) - timedelta(seconds=10)
    await db_session.commit()

    n = await reclaim_expired(db_session)
    await db_session.commit()
    assert n >= 1
    await db_session.refresh(job)
    assert job.status == STATUS_PENDING


@pytest.mark.asyncio
async def test_fail_marks_failed_when_attempts_exhausted(db_session: AsyncSession):
    job = await enqueue(db_session, "parse", {"document_id": "d"}, max_attempts=1)
    await db_session.commit()
    claimed = await claim(db_session)
    assert claimed is not None
    await fail(db_session, claimed.id, "boom", requeue=False)
    await db_session.commit()
    await db_session.refresh(job)
    assert job.status == STATUS_FAILED
    assert "boom" in (job.error or "")
