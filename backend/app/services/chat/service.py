"""
Serviço de orquestração do Copiloto.

Fluxo de uma mensagem:
1. Valida conversa existente e feature habilitada.
2. Recupera fontes citáveis (RAG + contexto do documento/análise).
3. Monta prompt e chama o LLM.
4. Valida a resposta (grounding obrigatório) e normaliza.
5. Persiste mensagens (user + assistant) com metadados.

O Copiloto é consultivo: nenhuma ação de escrita é aplicada em entidades de
negócio. Falhas do LLM resultam em resposta segura com warning, nunca em
quebra da conversa.
"""

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat import ChatConversation, ChatMessage
from app.services.chat.llm_adapter import ChatLLMProvider, get_chat_llm
from app.services.chat.prompts import build_messages
from app.services.chat.sources import build_sources
from app.services.chat.validator import ValidatedAnswer, validate_llm_answer


logger = logging.getLogger(__name__)


class ChatDisabledError(Exception):
    """Copiloto desabilitado por configuração."""


class ChatConversationNotFoundError(Exception):
    """Conversa inexistente."""


async def _persistir_mensagem(
    db: AsyncSession,
    conversation: ChatConversation,
    role: str,
    content: str,
    *,
    sources: list | None = None,
    grounded: bool = False,
    confidence: float | None = None,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
    warning: str | None = None,
) -> ChatMessage:
    mensagem = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        sources=sources or [],
        grounded=grounded,
        confidence=confidence,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        warning=warning,
    )
    db.add(mensagem)
    conversation.updated_at = _agora()
    await db.flush()
    return mensagem


def _agora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


async def send_message(
    db: AsyncSession,
    conversation_id: int,
    content: str,
    llm: ChatLLMProvider | None = None,
) -> ChatMessage:
    """Processa uma mensagem do usuário e retorna a resposta do assistente."""
    if not settings.chat_enabled:
        raise ChatDisabledError("Copiloto desabilitado.")

    conversation = await db.get(ChatConversation, conversation_id)
    if not conversation:
        raise ChatConversationNotFoundError("Conversa não encontrada.")

    await _persistir_mensagem(db, conversation, "user", content)
    logger.info(
        "chat.message.received conversation_id=%s length=%d",
        conversation_id, len(content),
    )

    try:
        fontes = await build_sources(
            db, content, conversation.context_json or {}
        )
    except Exception:
        logger.exception("Falha ao montar fontes do copiloto")
        fontes = []
    logger.info(
        "chat.sources.retrieved conversation_id=%s count=%d",
        conversation_id, len(fontes),
    )

    provider = None
    inicio = time.monotonic()
    try:
        provider = llm or get_chat_llm()
        system_prompt, user_prompt = build_messages(
            content, conversation.context_json or {}, fontes
        )
        logger.info(
            "chat.llm.requested provider=%s model=%s",
            provider.provider_name, provider.model_name,
        )
        raw = await provider.generate(system_prompt, user_prompt)
        latency_ms = int((time.monotonic() - inicio) * 1000)
        resposta: ValidatedAnswer = validate_llm_answer(
            raw, require_grounding=settings.chat_require_grounding
        )
    except Exception:
        logger.exception(
            "chat.llm.failed provider=%s",
            getattr(provider, "provider_name", "desconhecido"),
        )
        resposta = ValidatedAnswer(
            content=(
                "Não foi possível processar sua pergunta agora. "
                "Tente novamente em instantes."
            ),
            refused=True,
            reason="falha-llm",
        )
        latency_ms = int((time.monotonic() - inicio) * 1000)

    if resposta.refused:
        logger.info("chat.answer.refused conversation_id=%s", conversation_id)

    return await _persistir_mensagem(
        db,
        conversation,
        "assistant",
        resposta.content,
        sources=[c.model_dump() for c in resposta.citations],
        grounded=resposta.grounded,
        confidence=resposta.confidence,
        provider=getattr(provider, "provider_name", "desconhecido"),
        model=getattr(provider, "model_name", None),
        latency_ms=latency_ms,
        warning=resposta.reason,
    )
