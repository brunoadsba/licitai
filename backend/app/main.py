"""
Ponto de entrada da aplicação FastAPI.

Configura:
- CORS (allowlist de origens)
- Security headers
- Rate limiting
- Routers da API
- Health check
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, async_session_factory
from app.api.router import router
from app.utils.security import SecurityHeadersMiddleware, RateLimitMiddleware
from app.utils.logging_config import setup_logging


# Configurar logging estruturado (JSON) — sem dados sensíveis
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sistema de Análise de Termos de Referência",
    description=(
        "API para análise automatizada de Termos de Referência (TR) "
        "de licitações públicas usando Inteligência Artificial."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# --- Middleware (ordem importa: último adicionado = primeiro executado) ---

# Rate limiting (configurável via env, padrão 600 req/min)
app.add_middleware(RateLimitMiddleware, max_requests=settings.rate_limit_max, window_seconds=60)

# Security headers (CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# CORS — allowlist de origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Accept"],
    expose_headers=["Content-Disposition"],
)

# --- Routers ---
app.include_router(router)


# --- Health Check ---
@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check",
    description="Verifica se o sistema está operacional.",
)
async def health_check():
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "version": "0.1.0",
    }


@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        from app.models.document import Document, DocumentItem  # noqa: F401
        from app.models.analysis import Analysis, Correction  # noqa: F401
        from app.models.legal import LegalDocument, LegalChunk  # noqa: F401
        from app.models.comparison import (  # noqa: F401
            Fornecedor,
            Molde,
            Comparacao,
            ComparacaoResultado,
        )
        await conn.run_sync(Base.metadata.create_all)

    # Resetar análises pendentes órfãs de reinicializações anteriores
    try:
        from app.models.analysis import Analysis
        from sqlalchemy import select
        async with async_session_factory() as session:
            result = await session.execute(
                select(Analysis).where(Analysis.status.in_(["pending", "running"]))
            )
            orphaned = result.scalars().all()
            for an in orphaned:
                an.status = "error"
                an.error_message = "Análise interrompida por reinicialização do servidor backend."
            if orphaned:
                await session.commit()
                logger.info("Resetadas %d análises órfãs de sessões anteriores.", len(orphaned))
    except Exception as e:
        logger.warning("Não foi possível resetar análises órfãs no startup: %s", e)

    logger.info("Sistema de Análise de TR iniciado")
    logger.info("Provedor LLM: %s", settings.llm_provider)
    logger.info("Banco de dados: %s", "SQLite" if "sqlite" in settings.database_url else "PostgreSQL")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Sistema de Análise de TR encerrado")
