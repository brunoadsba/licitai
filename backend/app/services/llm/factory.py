"""
Factory + singleton do provedor LLM (extraído de `provider.py` p/ manter ≤300).

`get_llm_provider()` continua sendo o singleton com failover completo.
`get_llm_provider_for()` escolhe esse singleton, uma cadeia só local, ou bloqueia.
"""

import logging

from app.config import settings
from app.services.privacy import PrivacyPolicyError, log_policy_decision

logger = logging.getLogger(__name__)

_llm_provider_instance = None
_local_llm_provider_instance = None


def reset_llm_provider() -> None:
    """Descarta as instâncias singleton (uso em testes / reload de config)."""
    global _llm_provider_instance, _local_llm_provider_instance
    _llm_provider_instance = None
    _local_llm_provider_instance = None


def get_llm_provider():
    from app.services.llm.provider import FailoverProvider, _build_providers

    global _llm_provider_instance
    if _llm_provider_instance is not None:
        return _llm_provider_instance

    providers = _build_providers()

    if not providers:
        raise RuntimeError(
            "Nenhum provedor LLM configurado. Verifique LLM_PROVIDER e "
            "as chaves de API (GEMINI_API_KEY/GROQ_API_KEY) no .env."
        )

    if len(providers) == 1:
        inner = providers[0]
    else:
        logger.info(
            "Failover ativo: %s → %s",
            providers[0].provider_name,
            " → ".join(p.provider_name for p in providers[1:]),
        )
        inner = FailoverProvider(providers)

    from app.services.llm.limiter import wrap_with_limiter

    _llm_provider_instance = wrap_with_limiter(inner)
    return _llm_provider_instance


def _get_local_only_provider():
    """Singleton só Ollama. Não é o mesmo objeto do failover completo."""
    from app.services.llm.limiter import wrap_with_limiter
    from app.services.llm.provider import _build_local_providers

    global _local_llm_provider_instance
    if _local_llm_provider_instance is not None:
        return _local_llm_provider_instance

    providers = _build_local_providers()
    if not providers:
        raise PrivacyPolicyError(
            "Ollama local não está configurado para documento sigiloso."
        )
    _local_llm_provider_instance = wrap_with_limiter(providers[0])
    return _local_llm_provider_instance


def select_chat_llm(policy, injected, *, document_id: str | None, force_fake: bool):
    """Provedor do chat: nuvem, fake de teste, Ollama local ou bloqueio."""
    if policy.cloud_llm or force_fake:
        log_policy_decision(
            document_id=document_id, policy=policy, decision="allowed"
        )
        if injected is not None:
            return injected
        from app.services.chat.llm_adapter import get_chat_llm

        return get_chat_llm()
    return get_llm_provider_for(policy, document_id=document_id)


def get_llm_provider_for(policy, *, document_id: str | None = None):
    """
    Nuvem permitida → singleton atual.
    Primário Ollama e documento restrito → cadeia só local.
    Caso contrário → PrivacyPolicyError (sem construir cliente cloud).
    """
    if policy.cloud_llm:
        log_policy_decision(
            document_id=document_id, policy=policy, decision="allowed"
        )
        return get_llm_provider()

    if settings.llm_provider == "ollama":
        log_policy_decision(
            document_id=document_id, policy=policy, decision="allowed"
        )
        return _get_local_only_provider()

    log_policy_decision(
        document_id=document_id, policy=policy, decision="blocked"
    )
    raise PrivacyPolicyError()
