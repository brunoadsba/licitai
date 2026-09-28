"""
Harness de testes unitários do backend.

Força DATABASE_URL async (SQLite) antes de qualquer import de `app.*`,
para o engine de `app.database` não herdar `postgresql://` síncrono do `.env`
nem de variáveis já exportadas no shell.
"""

from __future__ import annotations

import asyncio
import os

import pytest
import sqlalchemy.ext.asyncio as _sa_async

_TRACKED_ENGINES: list = []
_real_create_async_engine = _sa_async.create_async_engine


def _tracking_create_async_engine(*args, **kwargs):
    engine = _real_create_async_engine(*args, **kwargs)
    _TRACKED_ENGINES.append(engine)
    return engine


_sa_async.create_async_engine = _tracking_create_async_engine


@pytest.fixture(autouse=True)
def _dispose_tracked_engines():
    yield
    for engine in _TRACKED_ENGINES:
        asyncio.run(engine.dispose())
    _TRACKED_ENGINES.clear()

# Sempre sobrescrever: `setdefault` falha se o shell já exportou DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["API_TOKEN"] = ""
# Chaves LLM zeradas: .env local com chaves reais não pode vazar para testes
# de factory/failover (cada teste liga o que precisa via monkeypatch).
for _key in ("GROQ_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY",
             "OPENROUTER_API_KEY", "HF_API_KEY", "COHERE_API_KEY",
             "NVIDIA_API_KEY", "SILICONFLOW_API_KEY", "ZAI_API_KEY",
             "DEEPSEEK_API_KEY", "LONGCAT_API_KEY", "OPENCODE_API_KEY",
             "POLLINATIONS_API_KEY"):
    os.environ[_key] = ""
# Lote 1 = fluxo unitário: .env local com ANALYSIS_BATCH_SIZE>1 (bulk) não
# pode mudar o comportamento coberto pela suíte (testes de lote usam monkeypatch).
os.environ["ANALYSIS_BATCH_SIZE"] = "1"
# Hunter desligado = fluxo padrão: .env local com MISS_HUNTER_ENABLED=true não
# pode injetar 2ª passada nos testes de engine/persistência.
os.environ["MISS_HUNTER_ENABLED"] = "false"
os.environ["MISS_HUNTER_MAX_ITEMS"] = "10"
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
