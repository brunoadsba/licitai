"""
Harness de testes unitários do backend.

Força DATABASE_URL async (SQLite) antes de qualquer import de `app.*`,
para o engine de `app.database` não herdar `postgresql://` síncrono do `.env`
nem de variáveis já exportadas no shell.
"""

from __future__ import annotations

import os

# Sempre sobrescrever: `setdefault` falha se o shell já exportou DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("CHAT_FORCE_FAKE_PROVIDER", "true")
