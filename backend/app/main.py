"""
Ponto de entrada da aplicação FastAPI.

Configura:
- CORS (allowlist de origens)
- Security headers
- Rate limiting
- Routers da API
- Health / livez / readyz
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import router
from app.config import settings
from app.database import async_session_factory, engine
from app.utils.logging_config import setup_logging
from app.utils.request_context import RequestIdMiddleware
from app.utils.security import RateLimitMiddleware, SecurityHeadersMiddleware

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema via Alembic em staging/production. create_all só em SQLite de desenvolvimento/teste.
    if settings.is_development and "sqlite" in settings.database_url:
        from app.database import Base

        async with engine.begin() as conn:
            from app.models.analysis import Analysis, Correction  # noqa: F401
            from app.models.chat import ChatConversation, ChatMessage  # noqa: F401
            from app.models.comparison import (  # noqa: F401
                Comparacao,
                ComparacaoResultado,
                Fornecedor,
                Molde,
            )
            from app.models.document import Document, DocumentItem  # noqa: F401
            from app.models.document_revision import DocumentRevision  # noqa: F401
            from app.models.job import Job  # noqa: F401
            from app.models.legal import LegalChunk, LegalDocument  # noqa: F401

            await conn.run_sync(Base.metadata.create_all)

    try:
        from sqlalchemy import select

        from app.models.analysis import Analysis

        async with async_session_factory() as session:
            # Só zera análises "running" (interrupção mid-flight).
            # pending fica para a fila de jobs / worker reclaim.
            result = await session.execute(
                select(Analysis).where(Analysis.status == "running")
            )
            orphaned = result.scalars().all()
            for an in orphaned:
                an.status = "error"
                an.error_message = (
                    "Análise interrompida por reinicialização do servidor backend."
                )
            if orphaned:
                await session.commit()
                logger.info(
                    "Resetadas %d análises running órfãs de sessões anteriores.",
                    len(orphaned),
                )
    except Exception as e:
        logger.warning("Não foi possível resetar análises órfãs no startup: %s", e)

    logger.info("Sistema de Análise de TR iniciado")
    logger.info("Provedor LLM: %s", settings.llm_provider)
    logger.info(
        "Banco de dados: %s",
        "SQLite" if "sqlite" in settings.database_url else "PostgreSQL",
    )

    yield

    logger.info("Sistema de Análise de TR encerrado")


app = FastAPI(
    title="Sistema de Análise de Termos de Referência",
    description=(
        "API para análise automatizada de Termos de Referência (TR) "
        "de licitações públicas usando Inteligência Artificial."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware, max_requests=settings.rate_limit_max, window_seconds=60)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Accept", "X-API-Token"],
    expose_headers=["Content-Disposition"],
)

app.include_router(router)


@app.get("/livez", tags=["Sistema"], summary="Liveness probe")
async def livez():
    """Sempre 200 se o processo estiver vivo."""
    return {"status": "alive"}


@app.get("/readyz", tags=["Sistema"], summary="Readiness probe")
async def readyz(response: Response):
    """503 se DB inacessível ou schema_version divergente."""
    checks: dict[str, str] = {"database": "ok", "schema": "ok"}
    ready = True

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            try:
                row = (
                    await conn.execute(
                        text(
                            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
                        )
                    )
                ).fetchone()
                current = row[0] if row else None
                if current != settings.expected_schema_version:
                    checks["schema"] = (
                        f"mismatch: got={current!r} "
                        f"expected={settings.expected_schema_version!r}"
                    )
                    ready = False
            except Exception:
                # Tabela ausente: em development com SQLite, tolerar; senão fail.
                if not settings.is_development:
                    checks["schema"] = "schema_meta unavailable"
                    ready = False
                else:
                    checks["schema"] = "skipped"
    except Exception:
        logger.exception("readyz: falha no banco")
        checks["database"] = "error"
        ready = False

    if not ready:
        response.status_code = 503
        return {"status": "not_ready", "checks": checks}
    from app.utils.metrics import metrics

    snap = metrics.snapshot()
    return {
        "status": "ready",
        "checks": checks,
        "metrics": {
            "job_queue_depth": snap["gauges"].get("job_queue_depth"),
            "llm_errors": snap["counters"].get("llm_errors", 0),
            "analysis_duration_avg_seconds": snap["analysis_duration_avg_seconds"],
        },
    }


@app.get("/metrics", tags=["Sistema"], summary="Métricas in-memory")
async def metrics_endpoint():
    from app.utils.metrics import metrics

    return metrics.snapshot()


@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check (legado)",
    description="Compatível com clientes antigos; preferir /livez e /readyz.",
)
async def health_check():
    database_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: falha ao conectar no banco")
        database_status = "error"

    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "provider": settings.llm_provider,
        "version": "0.1.0",
        "database": database_status,
    }
