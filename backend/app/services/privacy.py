"""Política de provedores: NULL e sigiloso são restritos (fail-closed)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

CLOUD_PROVIDERS = frozenset({"groq", "gemini"})
SIGILOSO_VALUES = frozenset({"sigiloso", "secreto", "confidential", "restricted"})
PUBLIC_VALUES = frozenset({"publico", "público", "interno", "public", "ostensivo"})

_BLOCKED_MESSAGE = (
    "Documento sigiloso ou sem classificação não pode ser enviado a provedor "
    "cloud. Classifique como público ou interno, ou use Ollama local."
)


class CloudPrivacyError(Exception):
    """Documento restrito bloqueado em provedor cloud."""

    def __init__(self, message: str = _BLOCKED_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


class PrivacyPolicyError(CloudPrivacyError):
    """Operação bloqueada pela política de provedores (não retentável)."""


@dataclass(frozen=True)
class ProviderPolicy:
    """Permissões de nuvem para uma classificação já resolvida."""

    classification: str | None
    restricted: bool
    cloud_llm: bool
    cloud_embeddings: bool
    llm_rerank: bool


def normalize_classification(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    return cleaned or None


def is_sigiloso(classification: str | None) -> bool:
    norm = normalize_classification(classification)
    return bool(norm and norm in SIGILOSO_VALUES)


def is_restricted(classification: str | None) -> bool:
    """NULL, sigiloso e qualquer valor que não seja público/interno."""
    norm = normalize_classification(classification)
    if norm is None:
        return True
    return norm not in PUBLIC_VALUES


def is_cloud_provider(provider: str | None = None) -> bool:
    return (provider or settings.llm_provider).lower() in CLOUD_PROVIDERS


def _dev_cloud_override() -> bool:
    return bool(settings.llm_allow_cloud and settings.app_env == "development")


def resolve_policy(classification: str | None) -> ProviderPolicy:
    """Resolve permissões. Não lê nem registra o conteúdo do documento."""
    norm = normalize_classification(classification)
    restricted = is_restricted(norm)
    allow_cloud = (not restricted) or _dev_cloud_override()
    # Restrito sem override: sem rerank LLM (RAG só textual). Override de
    # development segue o modo configurado, como o caminho público.
    rerank = bool(allow_cloud and settings.rag_rerank_mode == "llm")
    return ProviderPolicy(
        classification=norm,
        restricted=restricted,
        cloud_llm=allow_cloud,
        cloud_embeddings=allow_cloud,
        llm_rerank=rerank,
    )


def log_policy_decision(
    *,
    document_id: str | None,
    policy: ProviderPolicy,
    decision: str,
) -> None:
    """Registra só a decisão. Nunca o texto do documento ou da query."""
    logger.info(
        "privacy.decision document_id=%s classification=%s provider=%s decision=%s",
        document_id or "-",
        policy.classification or "unclassified",
        settings.llm_provider,
        decision,
    )


def assert_cloud_allowed_for_document(
    classification: str | None,
    *,
    provider: str | None = None,
) -> None:
    """
    Fail-closed na borda HTTP. Ollama primário não levanta: o engine usa
    a cadeia só local. Nos demais casos restritos, levanta PrivacyPolicyError.
    """
    policy = resolve_policy(classification)
    if policy.cloud_llm:
        return
    effective = (provider or settings.llm_provider).lower()
    if effective == "ollama":
        return
    raise PrivacyPolicyError()


def llm_rerank_allowed_for_document(
    classification: str | None,
    *,
    rerank_mode: str | None = None,
    provider: str | None = None,
) -> bool:
    """Rerank LLM só com modo `llm` e nuvem permitida. Restrito fica só textual."""
    mode = rerank_mode or settings.rag_rerank_mode
    if mode != "llm":
        return False
    policy = resolve_policy(classification)
    if not policy.cloud_llm:
        return False
    return True


def resolve_classification(
    *,
    form_value: str | None = None,
    header_value: str | None = None,
    document_classification: str | None = None,
) -> str | None:
    """Prioridade: form > header > persistido no documento."""
    for candidate in (form_value, header_value, document_classification):
        norm = normalize_classification(candidate)
        if norm:
            return norm
    return None


def _as_uuid(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def classification_for_chat(db: AsyncSession, conversation) -> str | None:
    """Documento ou análise vinculada vencem o payload. Conversa livre usa o contexto.

    Sem classificação explícita o retorno é None (restrito).
    """
    from app.models.analysis import Analysis
    from app.models.document import Document

    if getattr(conversation, "document_id", None):
        document = await db.get(Document, _as_uuid(conversation.document_id))
        if document is None:
            return None
        return document.classification

    if getattr(conversation, "analysis_id", None):
        analysis = await db.get(Analysis, _as_uuid(conversation.analysis_id))
        if analysis is None:
            return None
        document = await db.get(Document, analysis.document_id)
        if document is None:
            return None
        return document.classification

    context = getattr(conversation, "context_json", None) or {}
    return normalize_classification(context.get("classification"))
