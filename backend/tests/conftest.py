"""
Harness de testes unitários do backend.

Força DATABASE_URL async (SQLite) antes de qualquer import de `app.*`,
para o engine de `app.database` não herdar `postgresql://` síncrono do `.env`
nem de variáveis já exportadas no shell.
"""

from __future__ import annotations

import os

import pytest

# Sempre sobrescrever: `setdefault` falha se o shell já exportou DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["API_TOKEN"] = ""
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("CHAT_FORCE_FAKE_PROVIDER", "true")

_CLOUD_HOSTS = ("groq.com", "googleapis.com")


@pytest.fixture
def guard_against_cloud(monkeypatch):
    """Falha se um teste tocar Groq, Gemini ou HTTP de nuvem.

    Ollama local não entra na lista. A fixture é explícita: os testes do
    caminho de produção pedem ela. Não é autouse para não brigar com
    monkeypatch de generate feito pelo próprio teste.
    """
    calls: list[str] = []

    async def _blocked_generate(self, system_prompt, user_prompt):
        calls.append(getattr(self, "provider_name", "llm"))
        raise AssertionError(f"chamada cloud LLM: {calls[-1]}")

    async def _blocked_embed(self, text):
        calls.append("embeddings")
        raise AssertionError("chamada cloud embeddings")

    monkeypatch.setattr(
        "app.services.llm.groq_provider.GroqProvider.generate",
        _blocked_generate,
    )
    monkeypatch.setattr(
        "app.services.llm.gemini_provider.GeminiProvider.generate",
        _blocked_generate,
    )
    monkeypatch.setattr(
        "app.services.embeddings.gemini_provider.GeminiEmbeddingsProvider.embed",
        _blocked_embed,
    )

    import httpx

    original_send = httpx.AsyncClient.send

    async def _send(self, request, *args, **kwargs):
        url = str(getattr(request, "url", ""))
        if any(host in url for host in _CLOUD_HOSTS):
            calls.append(url)
            raise AssertionError(f"HTTP cloud bloqueado: {url}")
        return await original_send(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", _send)
    return calls
