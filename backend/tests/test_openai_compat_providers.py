"""Testes do provider OpenAI-compatível (Mistral/OpenRouter/HuggingFace).

Usa httpx.MockTransport: nenhuma chamada real de rede. Cobre geração,
429 (marcador do circuit breaker), erro transitório, resposta vazia,
health check e a ordem da factory com chaves presentes/ausentes.
"""

import asyncio

import httpx

from app.config import settings
from app.services.llm.openai_compat_provider import OpenAICompatProvider
from app.services.llm.provider import _build_providers


def _chat_ok(content="ok", usage=None):
    return httpx.Response(200, json={
        "choices": [{"message": {"content": content}}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 2,
                           "total_tokens": 12},
    })


def _provider(handler, name="mistral", model="m"):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        transport=transport, base_url="https://x.test",
        headers={"Authorization": "Bearer k"},
    )
    return OpenAICompatProvider(
        provider_name=name, api_key="k", model=model,
        base_url="https://x.test", client=client,
    )


def test_generate_retorna_texto():
    p = _provider(lambda req: _chat_ok("  feito  "))
    assert asyncio.run(p.generate("sys", "user")) == "feito"
    assert p.provider_name == "mistral"
    assert p.model_name == "m"


def test_generate_429_carrega_marcador():
    p = _provider(lambda req: httpx.Response(429, text="slow down"))
    try:
        asyncio.run(p.generate("sys", "user"))
        raise AssertionError("deveria falhar")
    except RuntimeError as e:
        assert "429" in str(e)


def test_generate_500_vira_runtime():
    p = _provider(lambda req: httpx.Response(500, text="boom"))
    try:
        asyncio.run(p.generate("sys", "user"))
        raise AssertionError("deveria falhar")
    except RuntimeError:
        pass


def test_generate_vazio_vira_runtime():
    p = _provider(lambda req: _chat_ok(""))
    try:
        asyncio.run(p.generate("sys", "user"))
        raise AssertionError("deveria falhar")
    except RuntimeError:
        pass


def test_health_check_ok_e_falha():
    assert asyncio.run(_provider(lambda req: _chat_ok("pong")).health_check()) is True
    assert asyncio.run(
        _provider(lambda req: httpx.Response(500, text="x")).health_check()
    ) is False


def test_factory_inclui_novos_providers(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "mistral_api_key", "mk")
    monkeypatch.setattr(settings, "mistral_model", "mm")
    monkeypatch.setattr(settings, "openrouter_api_key", "ok")
    monkeypatch.setattr(settings, "openrouter_model", "om")
    monkeypatch.setattr(settings, "hf_api_key", "")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["mistral", "openrouter"]


def test_factory_primario_novo_primeiro(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "groq_api_key", "gk")
    monkeypatch.setattr(settings, "groq_model", "gm")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "mistral_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "ok")
    monkeypatch.setattr(settings, "openrouter_model", "om")
    monkeypatch.setattr(settings, "hf_api_key", "hk")
    monkeypatch.setattr(settings, "hf_model", "hm")
    monkeypatch.setattr(settings, "hf_base_url", "https://hf.test/v1")
    chain = [p.provider_name for p in _build_providers()]
    assert chain[0] == "openrouter"
    assert "groq" in chain
    assert "huggingface" in chain
    assert "mistral" not in chain


def test_sem_chave_nao_envia_authorization():
    vistos = {}

    def handler(req):
        vistos["auth"] = req.headers.get("authorization")
        return _chat_ok("livre")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://x.test")
    p = OpenAICompatProvider(
        provider_name="pollinations", api_key="", model="openai",
        base_url="https://x.test", client=client,
    )
    assert asyncio.run(p.generate("sys", "user")) == "livre"
    assert vistos["auth"] is None


def test_factory_cohere_nvidia(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "cohere_api_key", "ck")
    monkeypatch.setattr(settings, "cohere_model", "command-r")
    monkeypatch.setattr(settings, "nvidia_api_key", "nvapi-x")
    monkeypatch.setattr(settings, "nvidia_model", "meta/llama-3.1-8b-instruct")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["cohere", "nvidia"]


def test_factory_siliconflow_zai_pollinations_com_chave(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key", "cohere_api_key",
                "nvidia_api_key"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "siliconflow_api_key", "sf")
    monkeypatch.setattr(settings, "siliconflow_model", "Qwen/Qwen3-8B")
    monkeypatch.setattr(settings, "zai_api_key", "zk")
    monkeypatch.setattr(settings, "zai_model", "glm-4.5-flash")
    monkeypatch.setattr(settings, "pollinations_api_key", "pk")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["siliconflow", "zai", "pollinations"]


def test_factory_pollinations_sem_chave_fica_fora(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key", "cohere_api_key",
                "nvidia_api_key", "siliconflow_api_key", "zai_api_key",
                "deepseek_api_key", "longcat_api_key", "opencode_api_key",
                "pollinations_api_key"):
        monkeypatch.setattr(settings, key, "")
    assert _build_providers() == []


def test_factory_deepseek_no_fallback(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key", "cohere_api_key",
                "nvidia_api_key", "siliconflow_api_key", "zai_api_key",
                "pollinations_api_key"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "deepseek_api_key", "dk")
    monkeypatch.setattr(settings, "deepseek_model", "deepseek-chat")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["deepseek"]


def test_factory_longcat_no_fallback(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key", "cohere_api_key",
                "nvidia_api_key", "siliconflow_api_key", "zai_api_key",
                "deepseek_api_key", "pollinations_api_key"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "longcat_api_key", "ak-x")
    monkeypatch.setattr(settings, "longcat_model", "LongCat-2.5-Preview")
    monkeypatch.setattr(settings, "longcat_base_url",
                          "https://api.longcat.chat/openai/v1")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["longcat"]


def test_factory_opencode_zen_no_fallback(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    for key in ("groq_api_key", "gemini_api_key", "mistral_api_key",
                "openrouter_api_key", "hf_api_key", "cohere_api_key",
                "nvidia_api_key", "siliconflow_api_key", "zai_api_key",
                "deepseek_api_key", "longcat_api_key",
                "pollinations_api_key"):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "opencode_api_key", "ok-x")
    monkeypatch.setattr(settings, "opencode_model", "mimo-v2.6-flash-free")
    monkeypatch.setattr(settings, "opencode_base_url",
                          "https://opencode.ai/inference/openai/v1")
    chain = [p.provider_name for p in _build_providers()]
    assert chain == ["opencode_zen"]
