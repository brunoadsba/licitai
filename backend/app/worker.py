"""
Worker asyncio de jobs duráveis.

Uso: `cd backend && PYTHONPATH=. python -m app.worker`

Processa tipos: analysis, comparacao, parse.
No startup: reclaim de leases expirados + órfãos (análises/comparações).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.analysis import Analysis
from app.models.comparison import Comparacao
from app.models.document import Document
from app.models.job import Job  # noqa: F401 — registra metadata
from app.services.analyzer.engine import run_analysis
from app.services.comparator.runner import executar_comparacao
from app.services.jobs import claim, complete, fail, queue_depth, reclaim_expired
from app.services.jobs.queue import claim_by_id
from app.services.upload_service import parse_e_inserir_itens
from app.utils.logging_config import setup_logging
from app.utils.metrics import metrics

setup_logging()
logger = logging.getLogger(__name__)

JOB_TYPES = ("analysis", "comparacao", "parse")


@dataclass
class _JobRef:
    id: uuid.UUID
    type: str
    payload: dict
    attempts: int = 0
    max_attempts: int = 3


async def _handle_orphans() -> None:
    """Análises/comparações pending|running sem job ativo → error ou requeue."""
    async with async_session_factory() as db:
        n = await reclaim_expired(db)
        if n:
            await db.commit()

        result = await db.execute(
            select(Analysis).where(Analysis.status.in_(["pending", "running"]))
        )
        analyses = result.scalars().all()
        for an in analyses:
            has_job = await _has_active_job(
                db, "analysis", {"analysis_id": str(an.id)}
            )
            if has_job:
                continue
            if an.status == "pending":
                from app.services.jobs import enqueue

                await enqueue(
                    db,
                    "analysis",
                    {
                        "analysis_id": str(an.id),
                        "document_id": str(an.document_id),
                    },
                )
                logger.info("orphan.analysis.requeued id=%s", an.id)
            else:
                an.status = "error"
                an.error_message = (
                    "Análise interrompida (lease/worker reiniciado sem job ativo)."
                )
                logger.warning("orphan.analysis.error id=%s", an.id)

        result = await db.execute(
            select(Comparacao).where(Comparacao.status.in_(["pending", "running"]))
        )
        comps = result.scalars().all()
        for comp in comps:
            has_job = await _has_active_job(
                db, "comparacao", {"comparacao_id": str(comp.id)}
            )
            if has_job:
                continue
            if comp.status == "pending":
                from app.services.jobs import enqueue

                payload = {
                    "comparacao_id": str(comp.id),
                    "tr_document_id": str(comp.tr_document_id),
                    "molde_id": str(comp.molde_id),
                    "propostas_ids": [
                        str(x) for x in (comp.propostas_ids or [])
                    ],
                }
                await enqueue(db, "comparacao", payload)
                logger.info("orphan.comparacao.requeued id=%s", comp.id)
            else:
                comp.status = "error"
                comp.error_message = (
                    "Comparação interrompida (lease/worker reiniciado sem job ativo)."
                )
                logger.warning("orphan.comparacao.error id=%s", comp.id)

        await db.commit()


async def _has_active_job(db, job_type: str, payload_match: dict) -> bool:
    result = await db.execute(
        select(Job).where(
            Job.type == job_type,
            Job.status.in_(["pending", "running"]),
        )
    )
    for job in result.scalars().all():
        payload = job.payload or {}
        if all(payload.get(k) == v for k, v in payload_match.items()):
            return True
    return False


async def process_job(job: _JobRef | Job) -> None:
    """Executa o handler do tipo do job e completa/falha."""
    started = datetime.now(timezone.utc)
    job_id = job.id
    job_type = job.type
    payload = dict(job.payload or {})

    try:
        if job_type == "analysis":
            await _run_analysis_job(payload)
        elif job_type == "comparacao":
            await _run_comparacao_job(payload)
        elif job_type == "parse":
            await _run_parse_job(payload)
        else:
            raise ValueError(f"Tipo de job desconhecido: {job_type}")

        async with async_session_factory() as db:
            await complete(db, job_id, result={"ok": True})
            await db.commit()

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        if job_type == "analysis":
            metrics.observe_analysis_duration(duration)
        metrics.set_gauge("job_last_success_seconds", duration)
        logger.info("job.ok id=%s type=%s duration=%.1fs", job_id, job_type, duration)

    except Exception as exc:
        logger.exception("job.error id=%s type=%s", job_id, job_type)
        metrics.inc("llm_errors" if "llm" in str(exc).lower() else "job_errors")
        async with async_session_factory() as db:
            await fail(db, job_id, str(exc), requeue=True)
            await db.commit()


async def _run_analysis_job(payload: dict) -> None:
    analysis_id = uuid.UUID(payload["analysis_id"])
    document_id = uuid.UUID(payload["document_id"])
    async with async_session_factory() as db:
        await run_analysis(db, analysis_id, document_id)
        await db.commit()


async def _run_comparacao_job(payload: dict) -> None:
    comparacao_id = uuid.UUID(payload["comparacao_id"])
    tr_document_id = uuid.UUID(payload["tr_document_id"])
    molde_id = uuid.UUID(payload["molde_id"])
    propostas_ids = [uuid.UUID(x) for x in payload.get("propostas_ids") or []]
    await executar_comparacao(
        comparacao_id, tr_document_id, molde_id, propostas_ids
    )


async def _run_parse_job(payload: dict) -> None:
    document_id = uuid.UUID(payload["document_id"])
    async with async_session_factory() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            raise RuntimeError(f"Documento {document_id} não encontrado para parse.")
        document.status = "parsing"
        await db.flush()
        ok = await parse_e_inserir_itens(db, document, document.file_type)
        if not ok:
            raise RuntimeError(document.error_message or "Falha no parse.")
        await db.commit()


async def process_job_by_id(job_id: uuid.UUID) -> None:
    """Claim + process de um job específico (modo in-process / BackgroundTasks)."""
    async with async_session_factory() as db:
        job = await claim_by_id(db, job_id)
        if not job:
            await db.commit()
            return
        ref = _JobRef(
            id=job.id,
            type=job.type,
            payload=dict(job.payload or {}),
            attempts=job.attempts,
            max_attempts=job.max_attempts,
        )
        await db.commit()
    await process_job(ref)


async def run_worker_loop(*, once: bool = False) -> None:
    """Loop principal do worker."""
    logger.info(
        "Worker iniciado poll=%.1fs lease=%ds types=%s",
        settings.worker_poll_interval_seconds,
        settings.job_lease_seconds,
        ",".join(JOB_TYPES),
    )
    await _handle_orphans()

    while True:
        try:
            async with async_session_factory() as db:
                await reclaim_expired(db)
                depth = await queue_depth(db)
                metrics.set_gauge("job_queue_depth", float(depth))
                job = await claim(db, job_types=list(JOB_TYPES))
                if job:
                    ref = _JobRef(
                        id=job.id,
                        type=job.type,
                        payload=dict(job.payload or {}),
                        attempts=job.attempts,
                        max_attempts=job.max_attempts,
                    )
                    await db.commit()
                else:
                    await db.commit()
                    ref = None

            if ref:
                await process_job(ref)
            elif once:
                break
            else:
                await asyncio.sleep(settings.worker_poll_interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("worker.loop.error")
            await asyncio.sleep(settings.worker_poll_interval_seconds)

        if once:
            break


def main() -> None:
    asyncio.run(run_worker_loop())


if __name__ == "__main__":
    main()
