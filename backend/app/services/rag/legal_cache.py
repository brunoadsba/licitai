"""Cache de retrieve: TTL, teto e isolamento por chave."""

from __future__ import annotations

import time

_CACHE_TTL_SECONDS = 3600
_CACHE_MAX_ENTRIES = 256

_legal_context_cache: dict[str, tuple[float, list, bool]] = {}
_cache_stats = {"hit": 0, "miss": 0}


def _clear_legal_context_cache() -> None:
    _legal_context_cache.clear()
    _cache_stats["hit"] = 0
    _cache_stats["miss"] = 0


def _evict_legal_cache() -> None:
    now = time.time()
    expired = [
        key
        for key, (ts, _chunks, _only) in _legal_context_cache.items()
        if now - ts >= _CACHE_TTL_SECONDS
    ]
    for key in expired:
        _legal_context_cache.pop(key, None)
    while len(_legal_context_cache) >= _CACHE_MAX_ENTRIES:
        oldest = min(_legal_context_cache, key=lambda k: _legal_context_cache[k][0])
        _legal_context_cache.pop(oldest, None)


def cache_get(key: str) -> tuple[list, bool] | None:
    cached = _legal_context_cache.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        _cache_stats["hit"] += 1
        return cached[1], cached[2]
    _cache_stats["miss"] += 1
    return None


def cache_put(key: str, chunks: list, quarantine_only: bool) -> None:
    _evict_legal_cache()
    _legal_context_cache[key] = (time.time(), chunks, quarantine_only)
