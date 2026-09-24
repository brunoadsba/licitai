"""Orquestração do Copiloto: política, fontes, LLM e persistência."""

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.chat import ChatConversation, ChatMessage
from app.services.chat.llm_adapter import ChatLLMProvider
from app.services.chat.prompts import build_messages
from app.services.chat.sources import (
    build_sources,
    hydrate_citations,
    source_ids_from,
)
from app.services.chat.validator import ValidatedAnswer, validate_llm_answer
from app.services.llm.factory import select_chat_llm
from app.services.privacy import classification_for_chat, resolve_policy
from app.services.chat.warnings_pt import (
    FALHA_LLM_MESSAGE,
    GREETING_MESSAGE,
    is_greeting,
    warning_message_pt,
)
from app.services.rag.quarantine import (
    QUARANTINE_ONLY_MESSAGE,
    consume_quarantine_only,
)

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
    retrieval_run_id: str | None = None,
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
        retrieval_run_id=retrieval_run_id,
    )
    db.add(mensagem)
    conversation.updated_at = _agora()
    await db.flush()
    return mensagem


def _agora():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


async def assert_chat_create_allowed(db: AsyncSession, conversation) -> None:
    """Bloqueia criação de conversa restrita sem montar cliente de nuvem."""
    from app.services.llm.factory import get_llm_provider_for
    from app.services.privacy import log_policy_decision

    policy = resolve_policy(await classification_for_chat(db, conversation))
    document_id = conversation.document_id or conversation.analysis_id
    if policy.cloud_llm or settings.chat_force_fake_provider:
        log_policy_decision(
            document_id=document_id, policy=policy, decision="allowed"
        )
        return
    get_llm_provider_for(policy, document_id=document_id)


async def resolve_chat_access(db: AsyncSession, conversation, injected=None):
    """Resolve política e provedor. Levanta PrivacyPolicyError se bloqueado."""
    policy = resolve_policy(await classification_for_chat(db, conversation))
    llm = select_chat_llm(
        policy,
        injected,
        document_id=conversation.document_id or conversation.analysis_id,
        force_fake=settings.chat_force_fake_provider,
    )
    return policy, llm


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

    policy, provider_llm = await resolve_chat_access(db, conversation, llm)

    await _persistir_mensagem(db, conversation, "user", content)
    logger.info(
        "chat.message.received conversation_id=%s length=%d",
        conversation_id, len(content),
    )

    # Cumprimento curto: resposta acolhedora sem gastar LLM / grounding
    if is_greeting(content):
        return await _persistir_mensagem(
            db,
            conversation,
            "assistant",
            GREETING_MESSAGE,
            grounded=False,
            provider="local",
            model="greeting",
            latency_ms=0,
        )

    try:
        montadas = await build_sources(
            db,
            content,
            conversation.context_json or {},
            allow_semantic=policy.cloud_embeddings,
            allow_llm_rerank=policy.llm_rerank,
            classification=policy.classification,
        )
        if isinstance(montadas, tuple):
            fontes, retrieval_run_id = montadas
        else:
            fontes, retrieval_run_id = montadas, None
    except Exception:
        logger.exception("Falha ao montar fontes do copiloto")
        fontes = []
        retrieval_run_id = None
    so_quarentena = consume_quarantine_only()
    logger.info(
        "chat.sources.retrieved conversation_id=%s count=%d quarantine_only=%s",
        conversation_id, len(fontes), so_quarentena,
    )
    if so_quarentena and not fontes:
        return await _persistir_mensagem(
            db,
            conversation,
            "assistant",
            QUARANTINE_ONLY_MESSAGE,
            grounded=False,
            provider="local",
            model="quarantine",
            latency_ms=0,
            warning=QUARANTINE_ONLY_MESSAGE,
            retrieval_run_id=retrieval_run_id,
        )

    provider = None
    inicio = time.monotonic()
    try:
        provider = provider_llm
        system_prompt, user_prompt = build_messages(
            content, conversation.context_json or {}, fontes
        )
        logger.info(
            "chat.llm.requested provider=%s model=%s",
            provider.provider_name, provider.model_name,
        )
        raw = await provider.generate(system_prompt, user_prompt)
        latency_ms = int((time.monotonic() - inicio) * 1000)
        from app.services.cost import estimate_tokens, record_operation_cost
        from app.utils.metrics import metrics

        metrics.observe_latency_ms(latency_ms)
        record_operation_cost("chat", estimate_tokens(system_prompt) + estimate_tokens(raw))
        resposta: ValidatedAnswer = validate_llm_answer(
            raw,
            require_grounding=settings.chat_require_grounding,
            valid_source_ids=source_ids_from(fontes),
        )
        resposta.citations = hydrate_citations(resposta.citations, fontes)
    except Exception:
        logger.exception(
            "chat.llm.failed provider=%s",
            getattr(provider, "provider_name", "desconhecido"),
        )
        resposta = ValidatedAnswer(
            content=FALHA_LLM_MESSAGE,
            refused=True,
            reason="falha-llm",
        )
        latency_ms = int((time.monotonic() - inicio) * 1000)

    if resposta.refused:
        logger.info(
            "chat.answer.refused conversation_id=%s reason=%s",
            conversation_id,
            resposta.reason,
        )

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
        warning=warning_message_pt(resposta.reason) if resposta.refused else None,
        retrieval_run_id=retrieval_run_id,
    )
