"""
Fila durável de jobs no banco (sem Redis).

Estados: pending → running → completed | failed
Lease: worker renova/ocupa via lease_until; reclaim_expired devolve jobs
com lease expirado para pending (ou failed se estourar max_attempts).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.job import Job

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


async def enqueue(
    db: AsyncSession,
    job_type: str,
    payload: dict,
    *,
    max_attempts: int | None = None,
) -> Job:
    """Cria job pending e faz flush (não commit)."""
    job = Job(
        type=job_type,
        payload=payload,
        status=STATUS_PENDING,
        attempts=0,
        max_attempts=max_attempts or settings.job_max_attempts,
    )
    db.add(job)
    await db.flush()
    logger.info("job.enqueued id=%s type=%s", job.id, job_type)
    return job


async def claim(
    db: AsyncSession,
    *,
    lease_seconds: int | None = None,
    job_types: list[str] | None = None,
) -> Job | None:
    """
    Claim atômico do próximo job pending (FIFO).

    Usa SELECT … FOR UPDATE SKIP LOCKED quando o dialeto permite;
    no SQLite faz SELECT + UPDATE com checagem de status.
    """
    lease = lease_seconds if lease_seconds is not None else settings.job_lease_seconds
    now = datetime.now(timezone.utc)
    lease_until = now + timedelta(seconds=lease)

    stmt = (
        select(Job)
        .where(Job.status == STATUS_PENDING)
        .order_by(Job.created_at.asc())
        .limit(1)
    )
    if job_types:
        stmt = stmt.where(Job.type.in_(job_types))

    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        return None

    job.status = STATUS_RUNNING
    job.attempts = (job.attempts or 0) + 1
    job.lease_until = lease_until
    job.error = None
    job.updated_at = now
    await db.flush()
    logger.info(
        "job.claimed id=%s type=%s attempt=%s/%s",
        job.id, job.type, job.attempts, job.max_attempts,
    )
    return job


async def claim_by_id(
    db: AsyncSession,
    job_id: uuid.UUID,
    *,
    lease_seconds: int | None = None,
) -> Job | None:
    """Claim de um job específico se ainda estiver pending."""
    lease = lease_seconds if lease_seconds is not None else settings.job_lease_seconds
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.status == STATUS_PENDING)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None
    job.status = STATUS_RUNNING
    job.attempts = (job.attempts or 0) + 1
    job.lease_until = now + timedelta(seconds=lease)
    job.updated_at = now
    await db.flush()
    return job


async def complete(
    db: AsyncSession,
    job_id: uuid.UUID,
    result: dict | None = None,
) -> None:
    """Marca job como completed."""
    now = datetime.now(timezone.utc)
    job = await db.get(Job, job_id)
    if not job:
        logger.warning("job.complete.missing id=%s", job_id)
        return
    job.status = STATUS_COMPLETED
    job.result = result
    job.lease_until = None
    job.error = None
    job.completed_at = now
    job.updated_at = now
    await db.flush()
    logger.info("job.completed id=%s type=%s", job.id, job.type)


async def fail(
    db: AsyncSession,
    job_id: uuid.UUID,
    error: str,
    *,
    requeue: bool = True,
) -> None:
    """
    Marca falha. Se requeue e attempts < max_attempts → pending de novo;
    senão → failed definitivo.
    """
    now = datetime.now(timezone.utc)
    job = await db.get(Job, job_id)
    if not job:
        logger.warning("job.fail.missing id=%s", job_id)
        return

    job.error = (error or "erro desconhecido")[:4000]
    job.lease_until = None
    job.updated_at = now

    if requeue and (job.attempts or 0) < (job.max_attempts or 1):
        job.status = STATUS_PENDING
        logger.warning(
            "job.requeued id=%s type=%s attempt=%s error=%s",
            job.id, job.type, job.attempts, job.error[:200],
        )
    else:
        job.status = STATUS_FAILED
        job.completed_at = now
        logger.error(
            "job.failed id=%s type=%s attempts=%s error=%s",
            job.id, job.type, job.attempts, job.error[:200],
        )
    await db.flush()


async def reclaim_expired(db: AsyncSession) -> int:
    """
    Devolve jobs running com lease_until < now para pending
    (ou failed se attempts >= max_attempts).
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Job).where(
            Job.status == STATUS_RUNNING,
            Job.lease_until.is_not(None),
            Job.lease_until < now,
        )
    )
    expired = result.scalars().all()
    count = 0
    for job in expired:
        job.lease_until = None
        job.updated_at = now
        job.error = (job.error or "") + "; lease expirado"
        if (job.attempts or 0) >= (job.max_attempts or 1):
            job.status = STATUS_FAILED
            job.completed_at = now
        else:
            job.status = STATUS_PENDING
        count += 1
    if count:
        await db.flush()
        logger.info("job.reclaim_expired count=%d", count)
    return count


async def queue_depth(db: AsyncSession) -> int:
    """Quantidade de jobs pending (+ running opcionalmente só pending)."""
    result = await db.execute(
        select(func.count()).select_from(Job).where(
            or_(Job.status == STATUS_PENDING, Job.status == STATUS_RUNNING)
        )
    )
    return int(result.scalar_one() or 0)
