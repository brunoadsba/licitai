"""
Testes de integração da API do Copiloto (/api/v1/chat).

Usam banco SQLite em memória e um fake provider LLM (nunca Gemini/Groq/
Ollama reais, nunca depende de .env). Cobre health, conversas, mensagens e
feedback com os guards 404/400/422 e a resposta assistente com fontes.
"""

import asyncio
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.chat import ChatConversation, ChatMessage
from app.services.chat.llm_adapter import get_chat_llm


class FakeLLM:
    """Provider determinístico para os testes — resposta JSON válida."""

    provider_name = "fake"
    model_name = "fake-chat"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "refused": False,
                "answer": "Resposta do Copiloto de teste.",
                "grounded": True,
                "confidence": 0.95,
                "citations": [
                    {
                        "type": "legal",
                        "reference": "Lei 14.133/2021, art. 5º",
                        "title": "Lei 14.133/2021",
                        "snippet": "Trecho citado...",
                    }
                ],
                "suggested_actions": [],
            },
            ensure_ascii=False,
        )


def _run(coroutine):
    return asyncio.run(coroutine)


def _montar_session() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_create())
    return async_sessionmaker(engine, expire_on_commit=False)


def _cliente(Session, llm=None):
    async def override_get_db():
        async with Session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chat_llm] = lambda: llm or FakeLLM()
    return ASGITransport(app=app)


def _limpar_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_chat_llm, None)


async def _criar_conversa(ac: AsyncClient, context=None, title="Conversa Teste"):
    response = await ac.post(
        "/api/v1/chat/conversations",
        json={
            "document_id": str(uuid.uuid4()),
            "context": context or {},
            "title": title,
        },
    )
    return response


async def _enviar_mensagem(ac: AsyncClient, conversa_id: int, content="Pergunta?"):
    return await ac.post(
        f"/api/v1/chat/conversations/{conversa_id}/messages",
        json={"content": content},
    )


class TestHealth:
    def test_health_retorna_configuracao(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/chat/health")
                return response.status_code, response.json()

        status, body = _run(_cenario())
        _limpar_overrides()
        assert status == 200
        assert body["enabled"] is True
        assert body["require_grounding"] is True
        assert body["top_k_sources"] > 0


class TestConversas:
    def test_criar_conversa_retorna_201(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await _criar_conversa(ac)

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 201
        body = response.json()
        assert body["id"] > 0
        assert body["title"] == "Conversa Teste"

    def test_criar_conversa_sem_contexto(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    "/api/v1/chat/conversations", json={}
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 201
        assert response.json()["context_json"] == {}

    def test_listar_conversas_paginado(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                s.add_all(
                    [
                        ChatConversation(title=f"Conv {i}", context_json={})
                        for i in range(3)
                    ]
                )
                await s.commit()

        _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.get(
                    "/api/v1/chat/conversations?limit=2&offset=0"
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestMensagens:
    def test_mensagem_em_conversa_inexistente_404(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await _enviar_mensagem(ac, 9999)

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 404

    def test_mensagens_de_conversa_inexistente_404(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.get(
                    "/api/v1/chat/conversations/9999/messages"
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 404

    def test_mensagens_de_conversa_vazia_200(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                conv = ChatConversation(title="Vazia", context_json={})
                s.add(conv)
                await s.commit()
                await s.refresh(conv)
                return conv.id

        conv_id = _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.get(
                    f"/api/v1/chat/conversations/{conv_id}/messages"
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 200
        assert response.json() == []

    def test_enviar_mensagem_retorna_resposta_assistente(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                conv = ChatConversation(title="Ativa", context_json={})
                s.add(conv)
                await s.commit()
                await s.refresh(conv)
                return conv.id

        conv_id = _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await _enviar_mensagem(ac, conv_id, "Explique o art. 5º?")

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "assistant"
        assert body["content"] == "Resposta do Copiloto de teste."
        assert body["grounded"] is True
        assert body["provider"] == "fake"
        assert body["latency_ms"] is not None
        assert len(body["sources"]) == 1
        assert body["sources"][0]["type"] == "legal"

    def test_enviar_mensagem_persiste_user_e_assistant(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                conv = ChatConversation(title="Historico", context_json={})
                s.add(conv)
                await s.commit()
                await s.refresh(conv)
                return conv.id

        conv_id = _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                await _enviar_mensagem(ac, conv_id, "Pergunta persistida?")
                async with Session() as s:
                    mensagens = (
                        await s.execute(select(ChatMessage).order_by(ChatMessage.id))
                    ).scalars().all()
                    return [(m.role, m.content) for m in mensagens]

        mensagens = _run(_cenario())
        _limpar_overrides()
        assert [r for r, _ in mensagens] == ["user", "assistant"]
        assert mensagens[0][1] == "Pergunta persistida?"

    def test_mensagem_vazia_422(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    "/api/v1/chat/conversations/1/messages",
                    json={"content": ""},
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 422

    def test_mensagem_muito_longa_422(self):
        Session = _montar_session()
        transport = _cliente(Session)
        conteudo = "a" * 2001

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await _enviar_mensagem(ac, 1, conteudo)

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 422


class TestFeedback:
    def test_feedback_em_mensagem_inexistente_404(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    "/api/v1/chat/messages/9999/feedback",
                    json={"rating": "up"},
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 404

    def test_feedback_com_rating_invalido_422(self):
        Session = _montar_session()
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    "/api/v1/chat/messages/1/feedback",
                    json={"rating": "meh"},
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 422

    def test_feedback_em_mensagem_do_usuario_400(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                conv = ChatConversation(title="Feedback", context_json={})
                s.add(conv)
                await s.commit()
                await s.refresh(conv)
                msg = ChatMessage(
                    conversation_id=conv.id, role="user", content="oi"
                )
                s.add(msg)
                await s.commit()
                await s.refresh(msg)
                return msg.id

        msg_id = _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    f"/api/v1/chat/messages/{msg_id}/feedback",
                    json={"rating": "up"},
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 400

    def test_feedback_em_resposta_assistente_200(self):
        Session = _montar_session()

        async def _criar():
            async with Session() as s:
                conv = ChatConversation(title="Feedback OK", context_json={})
                s.add(conv)
                await s.commit()
                await s.refresh(conv)
                msg = ChatMessage(
                    conversation_id=conv.id,
                    role="assistant",
                    content="resposta",
                    sources=[],
                    grounded=True,
                )
                s.add(msg)
                await s.commit()
                await s.refresh(msg)
                return msg.id

        msg_id = _run(_criar())
        transport = _cliente(Session)

        async def _cenario():
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                return await ac.post(
                    f"/api/v1/chat/messages/{msg_id}/feedback",
                    json={"rating": "up", "comment": "Muito útil"},
                )

        response = _run(_cenario())
        _limpar_overrides()
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["rating"] == "up"
