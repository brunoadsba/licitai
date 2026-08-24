"""
Interface abstrata para provedores de LLM.

Factory pattern com failover automático entre provedores reais:
- Provider primário configurado via LLM_PROVIDER
- Fallback automático para os demais provedores configurados
- Retry com backoff para erros transitórios (não-timeout, não-429)
- Circuit breaker por provedor: 429/quota abre cooldown e evita
  re-tentar um provedor esgotado em cada chamada
- Instância única (singleton) para que o estado de failover persista
  entre chamadas ao longo do processo
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)

# Cooldown aplicado a um provedor após erro de rate limit/quota (429).
RATE_LIMIT_COOLDOWN_SECONDS = 30.0
# Backoff antes do retry único de erros transitórios (rede/5xx).
TRANSIENT_RETRY_BACKOFF_SECONDS = 1.0

_RATE_LIMIT_MARKERS = ("429", "rate limit", "resource_exhausted", "quota", "tpd", "tpm")


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detecta erros de cota/rate limit a partir da mensagem da exceção."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


class LLMProvider(ABC):
    """Interface base para todos os provedores de LLM."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class FailoverProvider(LLMProvider):
    """
    Wrapper que tenta múltiplos provedores em ordem, com fallback automático.

    - Erros transitórios (rede, 5xx): 1 retry com backoff antes de falhar over.
    - Timeout NÃO é re-tentado (o timeout já consumiu o orçamento de espera).
    - Rate limit/quota (429): abre circuit breaker (cooldown) no provedor;
      chamadas seguintes começam direto pelos demais provedores.
    """

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("Pelo menos um provider é obrigatório.")
        self._providers = providers
        self._last_successful: LLMProvider | None = None
        # Circuit breaker: monotonic deadline até o qual cada provedor é pulado.
        self._cooldown_until: list[float] = [0.0] * len(providers)

    # --- Circuit breaker -------------------------------------------------

    def _ordered_providers(self) -> list[tuple[int, LLMProvider]]:
        """Provedores disponíveis (fora de cooldown), na ordem de prioridade."""
        now = time.monotonic()
        available = [
            (i, p) for i, p in enumerate(self._providers)
            if self._cooldown_until[i] <= now
        ]
        skipped = [
            f"{self._providers[i].provider_name} ({self._cooldown_until[i] - now:.0f}s restantes)"
            for i in range(len(self._providers))
            if self._cooldown_until[i] > now
        ]
        if skipped:
            logger.info(
                "Circuit breaker ativo — provedores em cooldown ignorados: %s",
                ", ".join(skipped),
            )
        # Se TODOS estiverem em cooldown, tenta mesmo assim (pior caso ≈ comportamento antigo).
        return available or list(enumerate(self._providers))

    def _record_success(self, index: int) -> None:
        self._last_successful = self._providers[index]
        if self._cooldown_until[index]:
            logger.info("Provedor %s recuperado — circuit fechado.", self._providers[index].provider_name)
        self._cooldown_until[index] = 0.0

    def _open_circuit(self, index: int, exc: Exception) -> None:
        provider = self._providers[index]
        self._cooldown_until[index] = time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
        logger.warning(
            "Rate limit/quota no provedor %s/%s — circuit aberto por %.0fs (%s)",
            provider.provider_name,
            provider.model_name,
            RATE_LIMIT_COOLDOWN_SECONDS,
            exc,
        )

    # --- Geração ----------------------------------------------------------

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        last_error: Exception | None = None

        for position, (index, provider) in enumerate(self._ordered_providers()):
            is_last_provider = position == len(self._providers) - 1
            attempts = 2  # 1 tentativa + 1 retry para erros transitórios

            for attempt in range(attempts):
                try:
                    started = time.perf_counter()
                    response = await asyncio.wait_for(
                        provider.generate(system_prompt, user_prompt),
                        timeout=settings.llm_timeout_seconds,
                    )
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    self._record_success(index)
                    if position > 0 or attempt > 0:
                        logger.info(
                            "Failover/retry: %s/%s assumiu após falha anterior",
                            provider.provider_name, provider.model_name,
                        )
                    logger.info(
                        "llm_call provider=%s model=%s latency_ms=%d chars=%d",
                        provider.provider_name,
                        provider.model_name,
                        latency_ms,
                        len(response),
                    )
                    return response

                except asyncio.TimeoutError as e:
                    # Timeout não é re-tentado: já consumiu llm_timeout_seconds.
                    last_error = e
                    remaining = (
                        "Tentando próximo..."
                        if not is_last_provider else "Nenhum fallback restante."
                    )
                    logger.warning(
                        "Provider %s/%s excedeu timeout de %.0fs. %s",
                        provider.provider_name, provider.model_name,
                        settings.llm_timeout_seconds, remaining,
                    )
                    break

                except Exception as e:
                    last_error = e
                    if _is_rate_limit_error(e):
                        self._open_circuit(index, e)
                        break  # retry imediato em 429 não adianta → próximo provedor

                    if attempt < attempts - 1:
                        logger.warning(
                            "Erro transitório no provider %s/%s: %s — retry em %.1fs",
                            provider.provider_name, provider.model_name,
                            e, TRANSIENT_RETRY_BACKOFF_SECONDS,
                        )
                        await asyncio.sleep(TRANSIENT_RETRY_BACKOFF_SECONDS)
                    else:
                        remaining = (
                            "Tentando próximo..." if not is_last_provider else "Nenhum fallback restante."
                        )
                        logger.warning(
                            "Provider %s/%s falhou após retry: %s. %s",
                            provider.provider_name, provider.model_name, e, remaining,
                        )

        raise RuntimeError(
            f"Todos os provedores LLM falharam. Último erro: {last_error}"
        ) from last_error

    async def health_check(self) -> bool:
        for provider in self._providers:
            if await provider.health_check():
                self._last_successful = provider
                return True
        return False

    @property
    def provider_name(self) -> str:
        if self._last_successful:
            return self._last_successful.provider_name
        return self._providers[0].provider_name

    @property
    def model_name(self) -> str:
        if self._last_successful:
            return self._last_successful.model_name
        return self._providers[0].model_name


def _build_providers() -> list[LLMProvider]:
    """Constrói lista de provedores reais disponíveis na ordem de prioridade."""
    providers: list[LLMProvider] = []
    primary = settings.llm_provider

    def _add_gemini():
        if settings.gemini_api_key and not any(p.provider_name == "gemini" for p in providers):
            from app.services.llm.gemini_provider import GeminiProvider
            providers.append(GeminiProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            ))

    def _add_groq():
        if settings.groq_api_key and not any(p.provider_name == "groq" for p in providers):
            from app.services.llm.groq_provider import GroqProvider
            providers.append(GroqProvider(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
            ))

    def _add_ollama():
        if not any(p.provider_name == "ollama" for p in providers):
            from app.services.llm.ollama_provider import OllamaProvider
            providers.append(OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            ))

    if primary == "gemini":
        _add_gemini()
        _add_groq()
    elif primary == "groq":
        _add_groq()
        _add_gemini()
    elif primary == "ollama":
        _add_ollama()
        _add_groq()
        _add_gemini()

    return providers


# Singleton: mantém estado de failover/circuit breaker entre chamadas.
_llm_provider_instance: LLMProvider | None = None


def reset_llm_provider() -> None:
    """Descarta a instância singleton (uso em testes / reload de config)."""
    global _llm_provider_instance
    _llm_provider_instance = None


def get_llm_provider() -> LLMProvider:
    """
    Factory — retorna o melhor provedor LLM disponível com failover.

    A instância é criada uma única vez por processo (singleton): o estado
    de failover (`_last_successful`) e os circuit breakers de rate limit
    persistem entre chamadas, evitando re-tentar o primário morto a cada
    item analisado.

    A ordem de prioridade é definida pelo LLM_PROVIDER no .env:
    - gemini → Gemini → Groq
    - groq → Groq → Gemini (se chave presente)
    - ollama → Ollama → Groq → Gemini (se chaves presentes)

    Levanta RuntimeError se nenhum provedor real estiver configurado
    (chave de API ausente para o provedor primário e seus fallbacks).
    """
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
        _llm_provider_instance = providers[0]
    else:
        logger.info(
            "Failover ativo: %s → %s",
            providers[0].provider_name,
            " → ".join(p.provider_name for p in providers[1:]),
        )
        _llm_provider_instance = FailoverProvider(providers)

    return _llm_provider_instance
