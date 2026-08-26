"""
Correlação de requisições nos logs.

Cada request HTTP recebe um request_id (herdado do header X-Request-ID quando
presente), propagado via contextvar para todas as linhas de log emitidas
durante o processamento e devolvido na resposta.
"""

import contextvars
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Injeta o request_id corrente em todo LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Atribui/propaga X-Request-ID e registra acesso com duração."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            if request.url.path != "/health":
                logging.getLogger(__name__).info(
                    "http.request method=%s path=%s status=%d duration_ms=%d",
                    request.method,
                    request.url.path,
                    response.status_code,
                    int((time.perf_counter() - started) * 1000),
                )
            return response
        finally:
            request_id_var.reset(token)
