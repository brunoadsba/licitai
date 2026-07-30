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
from app.api.router import router
from app.utils.security import SecurityHeadersMiddleware, RateLimitMiddleware


# Configurar logging — sem dados sensíveis
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
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

# Rate limiting (60 req/min para MVP single-user)
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)

# Security headers (CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# CORS — allowlist de origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
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
    logger.info("Sistema de Análise de TR iniciado")
    logger.info("Provedor LLM: %s", settings.llm_provider)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Sistema de Análise de TR encerrado")
