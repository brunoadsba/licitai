"""Hashes estáveis para fonte e texto normalizado."""

from __future__ import annotations

import hashlib


def sha256_text(content: str) -> str:
    """SHA-256 de texto UTF-8 (mesmo input → mesmo digest)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """SHA-256 de bytes brutos."""
    return hashlib.sha256(payload).hexdigest()
