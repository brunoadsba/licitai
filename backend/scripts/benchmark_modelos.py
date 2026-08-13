"""
Benchmark comparativo de modelos LLM para a análise de TRs.

Roda a análise real (mesmos prompts de produção, mesmos TRs fixture) com
vários modelos lado a lado e mede, por modelo:

- Aderência ao formato DE->PARA: % de itens cujo JSON parseia em pelo menos
  uma correção válida (validate_correction).
- Grounding: recall médio dos achados esperados (palavras-chave) nos textos
  das correções.
- Fundamentação: % de correções com fundamento legal (legal_basis) preenchido.
- Latência média por item (chamada LLM apenas).

Comparação padrão:
- groq:    llama-3.1-8b-instant (nuvem, padrão atual do projeto)
- hermes3: Hermes 3 8B local (privacidade — TRs sigilosos)
- qwen3:   qwen3:32b local (modelo local atual)

Uso:
    python scripts/benchmark_modelos.py                          # todos
    python scripts/benchmark_modelos.py --models groq            # só Groq
    python scripts/benchmark_modelos.py --models hermes3,qwen3   # só locais
    python scripts/benchmark_modelos.py --ollama-base-url http://localhost:11434

Requisitos:
- Groq: GROQ_API_KEY no .env (ou no ambiente).
- Ollama: servidor rodando com os modelos baixados:
      ollama pull hermes3
      ollama pull qwen3:32b

Saídas (em backend/):
- benchmark_modelos_report.json — métricas detalhadas por modelo
- benchmark_modelos_report.md  — tabela markdown comparativa
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _p in (BACKEND_DIR, SCRIPTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from benchmark import (  # noqa: E402
    _evaluate_expected,
    _generate_with_retry,
    _item_prompt,
    _parse_corrections,
    _system_prompt,
    _to_item,
)
from benchmark_fixtures import BENCHMARK_TRS  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.llm.ollama_provider import OllamaProvider  # noqa: E402
from app.services.llm.provider import LLMProvider  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
JSON_OUTPUT = BACKEND_DIR / "benchmark_modelos_report.json"
MD_OUTPUT = BACKEND_DIR / "benchmark_modelos_report.md"

# Intervalo entre itens para provedores de nuvem (free tier ~30 req/min).
CALL_DELAY_SECONDS = 2.0

# Rótulos por NOME de modelo (llm.model_name), não por ID de CLI.
MODEL_IDS = {
    "llama-3.1-8b-instant": "Groq llama-3.1-8b-instant (nuvem)",
    "hermes3": "Hermes 3 8B (Ollama local)",
    "qwen3:32b": "Qwen3 32B (Ollama local)",
}


def _build_model_providers(model_ids: list[str], ollama_base_url: str) -> list[LLMProvider]:
    """Instancia os providers pedidos; pula os que não têm credenciais."""
    providers: list[LLMProvider] = []
    for mid in model_ids:
        if mid == "groq":
            if not settings.groq_api_key:
                logger.warning("GROQ_API_KEY ausente — pulando modelo Groq.")
                continue
            from app.services.llm.groq_provider import GroqProvider

            providers.append(
                GroqProvider(api_key=settings.groq_api_key, model="llama-3.1-8b-instant")
            )
        elif mid == "hermes3":
            providers.append(
                OllamaProvider(base_url=ollama_base_url, model="hermes3")
            )
        elif mid == "qwen3":
            providers.append(
                OllamaProvider(base_url=ollama_base_url, model="qwen3:32b")
            )
        else:
            logger.warning(
                "Modelo desconhecido: %s (válidos: groq, hermes3, qwen3)", mid
            )
    return providers


async def _run_model(llm: LLMProvider) -> dict:
    """Roda a análise dos TRs fixture com um modelo e coleta métricas."""
    if not await llm.health_check():
        raise RuntimeError(
            f"Health check falhou para {llm.provider_name}/{llm.model_name}. "
            "Ollama: confira se o servidor está de pé e se o modelo foi baixado "
            "(ollama pull <modelo>)."
        )

    itens_total = 0
    itens_aderentes = 0
    recalls: list[float] = []
    correcoes_geradas = 0
    correcoes_fundamentadas = 0
    latencias: list[float] = []
    erros: list[str] = []
    e_nuvem = llm.provider_name == "groq"

    for tr in BENCHMARK_TRS:
        for item_data in tr["items"]:
            item = _to_item(item_data)
            expected = [
                e for e in tr["expected"] if e["item_number"] == item.item_number
            ]
            expected_issues = expected[0]["issues"] if expected else []
            itens_total += 1

            try:
                inicio = time.perf_counter()
                raw = await _generate_with_retry(
                    llm, _system_prompt(), _item_prompt(item)
                )
                latencia = time.perf_counter() - inicio
                latencias.append(latencia)

                corrections = _parse_corrections(raw)
                if corrections:
                    itens_aderentes += 1
                    correcoes_geradas += len(corrections)
                    correcoes_fundamentadas += sum(
                        1 for c in corrections if c.get("legal_basis")
                    )

                evaluation = _evaluate_expected(expected_issues, corrections)
                recalls.append(evaluation["recall"])

                logger.info(
                    "%s | item %s: %d correções, recall %.2f, latência %.1fs",
                    llm.model_name, item.item_number, len(corrections),
                    evaluation["recall"], latencia,
                )
            except Exception as e:  # noqa: BLE001 — item com falha não derruba o lote
                logger.exception(
                    "Falha no item %s (%s/%s)",
                    item.item_number, llm.provider_name, llm.model_name,
                )
                recalls.append(0.0)
                erros.append(f"{tr['nome']} / item {item.item_number}: {e}")

            if e_nuvem:
                await asyncio.sleep(CALL_DELAY_SECONDS)

    total_correcoes = correcoes_geradas or 1
    return {
        "provider": llm.provider_name,
        "modelo": llm.model_name,
        "rotulo": MODEL_IDS.get(llm.model_name, f"{llm.provider_name}/{llm.model_name}"),
        "itens": itens_total,
        "aderencia": itens_aderentes / itens_total if itens_total else 0.0,
        "itens_aderentes": itens_aderentes,
        "recall_medio": sum(recalls) / len(recalls) if recalls else 0.0,
        "correcoes": correcoes_geradas,
        "fundamentacao": correcoes_fundamentadas / total_correcoes,
        "correcoes_fundamentadas": correcoes_fundamentadas,
        "latencia_media_s": sum(latencias) / len(latencias) if latencias else 0.0,
        "erros": erros,
    }


def _render_markdown(resultados: list[dict]) -> str:
    linhas = [
        "# Benchmark comparativo de modelos — LicitAI",
        "",
        "Métricas por modelo sobre os TRs fixture (mesmos prompts de produção).",
        "",
        "| Modelo | Aderência DE→PARA | Recall (grounding) | Fundamentação | Correções | Latência média |",
        "|--------|-------------------|--------------------|---------------|-----------|----------------|",
    ]
    for r in resultados:
        linhas.append(
            f"| {r['rotulo']} | {r['aderencia']:.0%} "
            f"| {r['recall_medio']:.2f} | {r['fundamentacao']:.0%} "
            f"| {r['correcoes']} | {r['latencia_media_s']:.1f}s |"
        )
    linhas += [
        "",
        "**Como ler:**",
        "- **Aderência**: % de itens com pelo menos uma correção válida (JSON parseável).",
        "- **Recall**: fração dos problemas esperados detectados (proxy de grounding na Lei 14.133/21).",
        "- **Fundamentação**: % das correções com fundamento legal preenchido.",
        "- **Latência**: tempo da chamada LLM (não inclui parsing).",
        "",
        "_Gerado por `scripts/benchmark_modelos.py`._",
        "",
    ]
    return "\n".join(linhas)


async def _ensure_ollama_model(llm: LLMProvider) -> None:
    """Falha rápido com mensagem clara se o modelo não está baixado no Ollama."""
    if llm.provider_name != "ollama":
        return
    import httpx

    base_url = getattr(llm, "_base_url", None)
    if not base_url:
        return
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        response = await client.get("/api/tags")
        if response.status_code != 200:
            return
        modelos = {m.get("name") for m in response.json().get("models", [])}
        alvo = llm.model_name
        candidatos = {alvo, alvo.split(":")[0], f"{alvo}:latest"}
        if not modelos & candidatos:
            raise RuntimeError(
                f"Modelo '{alvo}' não baixado no Ollama. Rode: ollama pull {alvo}"
            )


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        default="groq,hermes3,qwen3",
        help="Modelos a comparar, separados por vírgula. Opções: groq, hermes3, qwen3.",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=None,
        help="URL do servidor Ollama (padrão: OLLAMA_BASE_URL do .env).",
    )
    parser.add_argument(
        "--no-md",
        action="store_true",
        help="Não gera a tabela markdown (benchmark_modelos_report.md).",
    )
    args = parser.parse_args()

    model_ids = [m.strip() for m in args.models.split(",") if m.strip()]
    ollama_base_url = args.ollama_base_url or settings.ollama_base_url

    providers = _build_model_providers(model_ids, ollama_base_url)
    if not providers:
        logger.error(
            "Nenhum modelo disponível. Confira GROQ_API_KEY (Groq) e o servidor "
            "Ollama com os modelos baixados."
        )
        sys.exit(1)

    logger.info("Modelos a comparar: %s", ", ".join(p.model_name for p in providers))
    resultados = []
    for llm in providers:
        try:
            await _ensure_ollama_model(llm)
            resultados.append(await _run_model(llm))
        except Exception as e:  # noqa: BLE001 — modelo indisponível não derruba o lote
            logger.error("Modelo %s/%s não executou: %s", llm.provider_name, llm.model_name, e)

    if not resultados:
        logger.error("Nenhum modelo executou com sucesso.")
        sys.exit(1)

    report = {"modelos": resultados}
    JSON_OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(_render_markdown(resultados))
    if not args.no_md:
        MD_OUTPUT.write_text(_render_markdown(resultados), encoding="utf-8")
        logger.info("Tabela salva em %s", MD_OUTPUT)
    logger.info("Relatório JSON salvo em %s", JSON_OUTPUT)


if __name__ == "__main__":
    asyncio.run(main())
