"""
Cache in-memory de Idempotency-Key para POSTs start_* (piloto single-user).

Mesma key + mesmo escopo → retorna job/entidade existente sem novo enqueue.
Sem migração: TTL 24h, max 5k keys com evicção FIFO. Processo local apenas.
"""

import time
from collections import OrderedDict

_MAX_KEYS = 5_000
_TTL_SECONDS = 24 * 3600

_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def _evict_if_needed() -> None:
    while len(_cache) > _MAX_KEYS:
        _cache.popitem(last=False)


def lookup(key: str) -> dict | None:
    entry = _cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    # Refresh LRU order sem renovar TTL.
    _cache.move_to_end(key)
    return value


def store(key: str, value: dict) -> None:
    _cache[key] = (time.monotonic() + _TTL_SECONDS, value)
    _cache.move_to_end(key)
    _evict_if_needed()


def clear() -> None:
    """Apenas para testes."""
    _cache.clear()
