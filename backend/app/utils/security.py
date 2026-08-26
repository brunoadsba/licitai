"""
Middleware e utilitários de segurança.

Implementa:
- Security headers (CSP, X-Frame-Options, etc.)
- Rate limiting simples (in-memory, adequado para single-user MVP)
- CORS configurado via allowlist
"""

import logging
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


async def require_api_token(request: Request) -> None:
    """Dependency de autenticação opcional para todas as rotas /api/v1."""
    expected = settings.api_token
    if not expected:
        return
    provided = request.headers.get("X-API-Token", "")
    if not secrets.compare_digest(provided.encode(), expected.encode()):
        logger.warning("Requisição sem token válido: %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=401,
            detail="Token de API ausente ou inválido.",
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança a todas as respostas."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Content Security Policy — restritivo
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self'"
        )

        # Prevenir clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevenir MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — desabilitar APIs desnecessárias
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=()"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting simples in-memory.
    Adequado para MVP single-user.
    Em produção, usar Redis ou similar.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Identificar cliente pelo IP
        client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        window_start = now - self.window_seconds

        # Limpar requisições antigas
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > window_start
        ]

        # Verificar limite
        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning("Rate limit excedido para IP: %s", client_ip)
            return Response(
                content='{"detail": "Muitas requisições. Tente novamente em breve."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Registrar requisição
        self._requests[client_ip].append(now)

        return await call_next(request)
