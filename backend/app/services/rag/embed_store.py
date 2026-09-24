"""Cache persistente de embeddings de consulta (Fase 7)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.utils.file_validation import UPLOAD_DIR

_MAX_FILES = 256


def _dir() -> Path:
    path = UPLOAD_DIR / "query_embed_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _key(query: str, provider: str, corpus_version: str, classification: str) -> str:
    raw = f"{query}|{provider}|{corpus_version}|{classification}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_vector(
    query: str, provider: str, corpus_version: str, classification: str
) -> list[float] | None:
    path = _dir() / f"{_key(query, provider, corpus_version, classification)}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        vec = data.get("vector")
        return [float(x) for x in vec] if isinstance(vec, list) else None
    except (OSError, TypeError, ValueError):
        return None


def store_vector(
    query: str,
    provider: str,
    corpus_version: str,
    classification: str,
    vector: list[float],
) -> None:
    folder = _dir()
    path = folder / f"{_key(query, provider, corpus_version, classification)}.json"
    path.write_text(
        json.dumps({"vector": vector, "provider": provider}, ensure_ascii=False),
        encoding="utf-8",
    )
    files = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for stale in files[:-_MAX_FILES]:
        stale.unlink(missing_ok=True)
