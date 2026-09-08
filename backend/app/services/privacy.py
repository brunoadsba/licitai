"""
Política de privacidade para documentos sigilosos vs provedores cloud.

Se o documento for classificado como `sigiloso`, o provedor for cloud
(groq/gemini) e `llm_allow_cloud=False`, a operação é recusada.
"""

from __future__ import annotations

from app.config import settings

CLOUD_PROVIDERS = frozenset({"groq", "gemini"})
SIGILOSO_VALUES = frozenset({"sigiloso", "secreto", "confidential", "restricted"})


class CloudPrivacyError(Exception):
    """Documento sigiloso bloqueado em provedor cloud."""

    def __init__(self, message: str = (
        "Documento classificado como sigiloso não pode ser enviado a "
        "provedor cloud quando LLM_ALLOW_CLOUD=false. Use Ollama local "
        "ou altere a classificação."
    )) -> None:
        super().__init__(message)
        self.message = message


def normalize_classification(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    return cleaned or None


def is_sigiloso(classification: str | None) -> bool:
    norm = normalize_classification(classification)
    return bool(norm and norm in SIGILOSO_VALUES)


def is_cloud_provider(provider: str | None = None) -> bool:
    return (provider or settings.llm_provider).lower() in CLOUD_PROVIDERS


def assert_cloud_allowed_for_document(
    classification: str | None,
    *,
    provider: str | None = None,
) -> None:
    """
    Fail-closed: levanta CloudPrivacyError se sigiloso + cloud + !llm_allow_cloud.
    """
    if not is_sigiloso(classification):
        return
    if not is_cloud_provider(provider):
        return
    if settings.llm_allow_cloud:
        return
    raise CloudPrivacyError()


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
