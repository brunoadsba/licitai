"""
Factory + singleton do provedor LLM (extraído de `provider.py` p/ manter ≤300).
"""

import logging

logger = logging.getLogger(__name__)

_llm_provider_instance = None


def reset_llm_provider() -> None:
    """Descarta a instância singleton (uso em testes / reload de config)."""
    global _llm_provider_instance
    _llm_provider_instance = None


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
