"""
Schemas Pydantic do Copiloto (chat consultivo).

Espelham o contrato da API v1 de chat. `context` da conversa é um dict
opaco (JSON) usado como contexto para o LLM, sem valores sensíveis.
"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    BeforeValidator,
    Field,
    field_validator,
)

from app.config import settings

def _ensure_tz(v: datetime) -> datetime:
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


AwareDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]

ChatCitationType = Literal["legal", "analysis", "correction", "document_item"]


class ChatCitation(BaseModel):
    """Citação de uma fonte utilizada na resposta."""

    type: ChatCitationType
    reference: str
    title: str = ""
    snippet: str = ""


class ChatSuggestedAction(BaseModel):
    """Ação sugerida pelo LLM (descartada no MVP — não é aplicada)."""

    action: str
    description: str = ""


class ChatConversationCreate(BaseModel):
    """Payload para criar uma conversa."""

    document_id: str | None = None
    analysis_id: str | None = None
    context: dict = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=200)


class ChatMessageCreate(BaseModel):
    """Payload para enviar uma mensagem."""

    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def _validar_tamanho(cls, v: str) -> str:
        if len(v) > settings.chat_max_message_length:
            raise ValueError(
                f"Mensagem excede o limite de {settings.chat_max_message_length} caracteres."
            )
        return v


class ChatFeedbackCreate(BaseModel):
    """Feedback do usuário sobre uma resposta."""

    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=1000)


class ChatConversationResponse(BaseModel):
    """Conversa (visão de listagem)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str | None = None
    analysis_id: str | None = None
    context_json: dict = Field(default_factory=dict)
    title: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ChatMessageResponse(BaseModel):
    """Mensagem (user ou assistant) de uma conversa."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[ChatCitation] = Field(default_factory=list)
    grounded: bool = False
    confidence: float | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    warning: str | None = None
    created_at: AwareDatetime


class ChatHealthResponse(BaseModel):
    """Status operacional do Copiloto."""

    enabled: bool
    require_grounding: bool
    top_k_sources: int
    max_message_length: int
    force_fake_provider: bool
    llm_provider: str


class ChatFeedbackResponse(BaseModel):
    """Confirmação de feedback registrado."""

    message_id: int
    rating: str
    status: str = "ok"
