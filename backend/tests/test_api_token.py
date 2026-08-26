"""
Testes do token opcional de API (require_api_token).

Com API_TOKEN vazio (default) nenhuma rota exige token — comportamento
histórico do piloto. Definido, /api/v1 exige o header X-API-Token.
"""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


def _run(coroutine):
    return asyncio.run(coroutine)


def _status_com_token(token_configurado: str, header: str | None):
    async def _cenario():
        original = settings.api_token
        settings.api_token = token_configurado
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                headers = {"X-API-Token": header} if header is not None else {}
                response = await ac.get("/api/v1/chat/health", headers=headers)
            return response.status_code
        finally:
            settings.api_token = original

    return _run(_cenario())


def test_sem_token_configurado_requisicoes_passam():
    assert _status_com_token("", None) == 200


def test_token_configurado_exige_header():
    assert _status_com_token("segredo", None) == 401


def test_token_errado_e_rejeitado():
    assert _status_com_token("segredo", "errado") == 401


def test_token_correto_passa():
    assert _status_com_token("segredo", "segredo") == 200
