"""
Limitador global de concorrência LLM.

Wrapa qualquer LLMProvider com um asyncio.Semaphore baseado em
settings.llm_global_concurrency.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.services.llm.provider import LLMProvider
from app.utils.metrics import metrics

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_semaphore_limit: int | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore, _semaphore_limit
    limit = max(1, settings.llm_global_concurrency)
    if _semaphore is None or _semaphore_limit != limit:
        _semaphore = asyncio.Semaphore(limit)
        _semaphore_limit = limit
        logger.info("llm.limiter.semaphore limit=%d", limit)
    return _semaphore


class LimitedLLMProvider(LLMProvider):
    """Decorator que serializa generate() pelo semáforo global."""

    def __init__(self, inner: LLMProvider):
        self._inner = inner

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        sem = _get_semaphore()
        async with sem:
            try:
                return await self._inner.generate(system_prompt, user_prompt)
            except Exception:
                metrics.inc("llm_errors")
                raise

    async def health_check(self) -> bool:
        return await self._inner.health_check()

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        return self._inner.model_name


def wrap_with_limiter(provider: LLMProvider) -> LLMProvider:
    """Envolve provider com limitador (idempotente se já Limited)."""
    if isinstance(provider, LimitedLLMProvider):
        return provider
    return LimitedLLMProvider(provider)


def reset_limiter() -> None:
    """Reseta semáforo (testes)."""
    global _semaphore, _semaphore_limit
    _semaphore = None
    _semaphore_limit = None
