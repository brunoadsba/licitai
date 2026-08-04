"""
Benchmark de qualidade da análise (Fase 2.3).

Roda a análise real (LLM) + revisão cruzada sobre TRs fixture e mede
recall/precisão/F1 por dimensão e por TR.

- Recall: fração dos problemas esperados (palavras-chave) detectados nas
  correções mantidas após a revisão.
- Precisão: fração das correções geradas mantidas pelo revisor (proxy
  automático; uma anotação humana completa não é viável em lote).

Gera relatório em `backend/benchmark_report.json` e imprime no console.

Uso:
    python scripts/benchmark.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

from app.services.llm import get_llm_provider

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_fixtures import BENCHMARK_TRS, LEGAL_CONTEXT  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "benchmark_report.json"

DIMENSIONS = ["juridica", "tecnica", "redacao", "estrutural"]

RETRIES = 3
RETRY_DELAY_SECONDS = 20.0
CALL_DELAY_SECONDS = 3.0


async def _generate_with_retry(llm, system_prompt: str, user_prompt: str) -> str:
    """Chama o LLM com retry/backoff para lidar com rate limits transitórios."""
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            return await llm.generate(system_prompt, user_prompt)
        except Exception as e:  # noqa: BLE001 — taxa de cota deve continuar
            last_error = e
            logger.warning(
                "Falha na chamada LLM (tentativa %d/%d): %s",
                attempt,
                RETRIES,
                e,
            )
            if attempt < RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def _to_item(item: dict) -> SimpleNamespace:
    return SimpleNamespace(
        item_number=item["item_number"],
        title=item.get("title"),
        content=item["content"],
        page_number=item.get("page_number"),
    )


def _matches_keyword(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def _corrections_text(corrections: list[dict]) -> str:
    return " ".join(
        f"{c.get('problem', '')} {c.get('situation', '')} {c.get('original_text', '')} "
        f"{c.get('suggested_text', '')} {c.get('justification', '')} {c.get('risk', '')}"
        for c in corrections
    )


def _evaluate_expected(expected: list[dict], corrections: list[dict]) -> dict:
    """Calcula recall por problema esperado."""
    text = _corrections_text(corrections)
    hits = 0
    total = len(expected)
    for issue in expected:
        if _matches_keyword(text, issue["keyword"]):
            hits += 1
    return {"recall": hits / total if total else 1.0, "hits": hits, "total": total}


async def run_benchmark() -> dict:
    """Executa o benchmark sobre todos os TRs fixture."""
    llm = get_llm_provider()
    results = []

    for tr in BENCHMARK_TRS:
        tr_result = {
            "nome": tr["nome"],
            "items": [],
            "recall": 0.0,
            "precision": 0.0,
            "f1": 0.0,
            "generated": 0,
            "kept": 0,
            "erros": 0,
        }
        total_generated = 0
        total_kept = 0
        recalls = []

        for item_data in tr["items"]:
            item = _to_item(item_data)
            expected = [
                e
                for e in tr["expected"]
                if e["item_number"] == item.item_number
            ]
            expected_issues = expected[0]["issues"] if expected else []

            try:
                corrections = await _generate_with_retry(
                    llm,
                    _system_prompt(),
                    _item_prompt(item),
                )
                corrections = _parse_corrections(corrections)
                await asyncio.sleep(CALL_DELAY_SECONDS)

                decisions = await _review_with_retry(llm, item, corrections)
                kept_statuses = {
                    d["correction_index"]: d["status"] for d in decisions
                }
                kept = [
                    c
                    for i, c in enumerate(corrections)
                    if kept_statuses.get(i, "pendente") != "rejeitada"
                ]

                evaluation = _evaluate_expected(expected_issues, kept)
                recalls.append(evaluation["recall"])
                total_generated += len(corrections)
                total_kept += len(kept)
                erro = None
            except Exception as e:  # noqa: BLE001 — item com falha não quebra o lote
                logger.exception(
                    "Falha ao processar item %s do TR '%s'",
                    item.item_number,
                    tr["nome"],
                )
                evaluation = {"recall": 0.0, "hits": 0, "total": len(expected_issues)}
                recalls.append(0.0)
                kept = []
                erro = str(e)[:500]

            tr_result["items"].append(
                {
                    "item_number": item.item_number,
                    "generated": len(corrections) if not erro else 0,
                    "kept": len(kept),
                    "rejected": (len(corrections) - len(kept)) if not erro else 0,
                    "expected_hits": evaluation["hits"],
                    "expected_total": evaluation["total"],
                    "recall": evaluation["recall"],
                    "categories_kept": _count_categories(kept),
                    "erro": erro,
                }
            )

        tr_result["generated"] = total_generated
        tr_result["kept"] = total_kept
        tr_result["erros"] = sum(
            1 for i in tr_result["items"] if i["erro"]
        )
        tr_result["recall"] = sum(recalls) / len(recalls) if recalls else 0.0
        tr_result["precision"] = (
            total_kept / total_generated if total_generated else 1.0
        )
        tr_result["f1"] = _f1(tr_result["recall"], tr_result["precision"])
        results.append(tr_result)

    return {
        "trs": results,
        "resumo": _summary(results),
    }


async def _review_with_retry(llm, item, corrections: list[dict]) -> list[dict]:
    """Roda a revisão com retry; em falha, mantém tudo (nenhuma rejeição)."""
    try:
        raw = await _generate_with_retry(
            llm,
            _review_system_prompt(),
            _review_prompt(item, corrections),
        )
        return _parse_decisions(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("Revisão indisponível para item %s: %s", item.item_number, e)
        return []


def _parse_decisions(raw: str) -> list[dict]:
    """Converte a resposta crua do revisor em decisões normalizadas."""
    from app.services.analyzer.json_utils import parse_json_response

    parsed = parse_json_response(raw)
    if isinstance(parsed, dict):
        parsed = parsed.get("review", [])
    if not isinstance(parsed, list):
        return []
    return [
        {
            "correction_index": d.get("correction_index", 0),
            "status": str(d.get("status", "aprovada")).lower(),
        }
        for d in parsed
        if isinstance(d, dict)
    ]


def _system_prompt() -> str:
    from app.services.analyzer.prompts import SYSTEM_PROMPT

    return SYSTEM_PROMPT


def _item_prompt(item) -> str:
    from app.services.analyzer.prompts import ITEM_ANALYSIS_PROMPT

    return ITEM_ANALYSIS_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        page_number=item.page_number or "N/A",
        item_content=item.content[:8000],
        legal_context=LEGAL_CONTEXT,
    )


def _review_system_prompt() -> str:
    from app.services.analyzer.prompts import REVIEW_SYSTEM_PROMPT

    return REVIEW_SYSTEM_PROMPT


def _review_prompt(item, corrections: list[dict]) -> str:
    from app.services.analyzer.prompts import REVIEW_PROMPT

    return REVIEW_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        item_content=item.content[:8000],
        legal_context=LEGAL_CONTEXT,
        corrections_summary=_corrections_summary(corrections),
    )


def _corrections_summary(corrections: list[dict]) -> str:
    parts = []
    for i, c in enumerate(corrections):
        parts.append(
            f"[{i}] Categoria: {c.get('category', '?')} | "
            f"Severidade: {c.get('severity', '?')}\n"
            f"  Problema: {c.get('problem', '')}\n"
            f"  Trecho original: {c.get('original_text', '')}\n"
            f"  Texto sugerido: {c.get('suggested_text', '')}\n"
            f"  Fundamento: {c.get('legal_basis') or 'não informado'}\n"
            f"  Justificativa: {c.get('justification', '')}"
        )
    return "\n\n".join(parts)


def _parse_corrections(raw: str) -> list[dict]:
    """Converte a resposta crua do LLM em correções normalizadas."""
    from app.services.analyzer.json_utils import (
        parse_json_response,
        sanitize_correction,
        validate_correction,
    )

    parsed = parse_json_response(raw)
    return [
        sanitize_correction(c)
        for c in parsed
        if isinstance(c, dict) and validate_correction(c)
    ]


def _count_categories(corrections: list[dict]) -> dict[str, int]:
    counts = {d: 0 for d in DIMENSIONS}
    for c in corrections:
        cat = c.get("category", "tecnica")
        if cat in counts:
            counts[cat] += 1
    return counts


def _f1(recall: float, precision: float) -> float:
    if recall + precision == 0:
        return 0.0
    return 2 * recall * precision / (recall + precision)


def _summary(results: list[dict]) -> dict:
    recalls = [r["recall"] for r in results]
    precisions = [r["precision"] for r in results]
    return {
        "trs": len(results),
        "recall_media": sum(recalls) / len(recalls) if recalls else 0.0,
        "precision_media": sum(precisions) / len(precisions) if precisions else 0.0,
        "f1_media": _f1(
            sum(recalls) / len(recalls) if recalls else 0.0,
            sum(precisions) / len(precisions) if precisions else 0.0,
        ),
    }


async def main() -> None:
    """Roda o benchmark e grava o relatório."""
    logger.info("Iniciando benchmark de qualidade (LLM real)...")
    report = await run_benchmark()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    logger.info("Relatório salvo em %s", OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
