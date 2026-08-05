"""
Endpoints do Copiloto (chat consultivo) — API v1.

O chat é somente-leitura em relação às entidades de negócio: cria conversas
e mensagens próprias, consulta análises/documentos como contexto e nunca
aplica ações sugeridas pelo LLM.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import (
    ChatConversationCreate,
    ChatConversationResponse,
    ChatFeedbackCreate,
    ChatFeedbackResponse,
    ChatHealthResponse,
    ChatMessageCreate,
    ChatMessageResponse,
)
from app.services.chat.llm_adapter import ChatLLMProvider, get_chat_llm
from app.services.chat.service import (
    ChatConversationNotFoundError,
    ChatDisabledError,
    send_message,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Copiloto"])


@router.get(
    "/health",
    response_model=ChatHealthResponse,
    summary="Status do Copiloto",
    description="Indica se o chat está habilitado e como está configurado.",
)
async def chat_health():
    """Retorna o estado operacional do Copiloto."""
    return ChatHealthResponse(
        enabled=settings.chat_enabled,
        require_grounding=settings.chat_require_grounding,
        top_k_sources=settings.chat_top_k_sources,
        max_message_length=settings.chat_max_message_length,
        force_fake_provider=settings.chat_force_fake_provider,
        llm_provider=settings.llm_provider,
    )


@router.post(
    "/conversations",
    response_model=ChatConversationResponse,
    status_code=201,
    summary="Criar conversa",
    description="Cria uma conversa consultiva, opcionalmente vinculada a um documento/análise.",
)
async def create_conversation(
    payload: ChatConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria uma nova conversa do Copiloto."""
    conversa = ChatConversation(
        document_id=payload.document_id,
        analysis_id=payload.analysis_id,
        context_json=payload.context or {},
        title=payload.title,
    )
    db.add(conversa)
    await db.flush()
    logger.info(
        "chat.conversation.created conversation_id=%s document_id=%s analysis_id=%s",
        conversa.id, conversa.document_id, conversa.analysis_id,
    )
    return conversa


@router.get(
    "/conversations",
    response_model=list[ChatConversationResponse],
    summary="Listar conversas",
    description="Lista conversas ordenadas pela última atualização (decrescente).",
)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista conversas (paginado por updated_at desc)."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    result = await db.execute(
        select(ChatConversation)
        .order_by(ChatConversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ChatMessageResponse],
    summary="Mensagens de uma conversa",
    description="Retorna todas as mensagens de uma conversa, na ordem cronológica.",
)
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Lista mensagens de uma conversa."""
    conversa = await db.get(ChatConversation, conversation_id)
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.id)
    )
    return result.scalars().all()


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    summary="Enviar mensagem",
    description=(
        "Processa uma mensagem do usuário e retorna a resposta do assistente, "
        "com fontes citadas e metadados de confiança."
    ),
)
async def send_message_endpoint(
    conversation_id: int,
    payload: ChatMessageCreate,
    llm: ChatLLMProvider = Depends(get_chat_llm),
    db: AsyncSession = Depends(get_db),
):
    """Envia uma mensagem e retorna a resposta do Copiloto."""
    try:
        return await send_message(
            db, conversation_id, payload.content, llm=llm
        )
    except ChatDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ChatConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/messages/{message_id}/feedback",
    response_model=ChatFeedbackResponse,
    summary="Feedback de resposta",
    description="Registra feedback (up/down) sobre uma resposta do assistente.",
)
async def send_feedback(
    message_id: int,
    payload: ChatFeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    """Registra feedback do usuário sobre uma resposta."""
    mensagem = await db.get(ChatMessage, message_id)
    if not mensagem:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
    if mensagem.role != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Apenas respostas do assistente podem receber feedback.",
        )
    mensagem.feedback_rating = payload.rating
    mensagem.feedback_comment = payload.comment
    await db.flush()
    logger.info(
        "chat.feedback.received message_id=%s rating=%s",
        message_id, payload.rating,
    )
    return ChatFeedbackResponse(
        message_id=message_id,
        rating=payload.rating,
        status="ok",
    )
