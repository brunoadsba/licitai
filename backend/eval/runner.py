"""Executa o conjunto curado contra o retrieve() e grava baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.corpus_version import compute_corpus_version
from app.services.rag.retriever import _clear_legal_context_cache, retrieve
from eval.metrics import ndcg_at_k, percentile, recall_at_k, reciprocal_rank
from eval.schema import EvalCase, EvalDataset

EVAL_DIR = Path(__file__).resolve().parent
CASES_PATH = EVAL_DIR / "cases.json"
BASELINE_CI_PATH = EVAL_DIR / "baseline.ci.json"


def load_dataset(path: Path | None = None) -> EvalDataset:
    raw = json.loads((path or CASES_PATH).read_text(encoding="utf-8"))
    return EvalDataset.model_validate(raw)


def _norm_article(article: str) -> str:
    import re

    match = re.search(r"(\d+[a-z]?)", (article or "").lower())
    return match.group(1) if match else (article or "").strip()


def _key(law_number: str, article: str) -> tuple[str, str]:
    return (law_number.strip(), _norm_article(article))


def _expected_keys(case: EvalCase) -> set[tuple[str, str]]:
    return {_key(e.law_number, e.article) for e in case.expected_laws}


def _score_case(case: EvalCase, ranked: list[tuple[str, str]], texts: list[str]) -> dict:
    expected = _expected_keys(case)
    hits = [item in expected for item in ranked]
    relevances = [1.0 if h else 0.0 for h in hits]
    found = {item for item, hit in zip(ranked, hits, strict=False) if hit}
    if case.expect_empty:
        if case.category == "nao_autorizado":
            empty_ok = not any(
                "TCU" in law or "Súmula" in law for law, _art in ranked
            )
        else:
            empty_ok = len(ranked) == 0
        recall1 = recall5 = 1.0 if empty_ok else 0.0
        rr = recall5
        ndcg = recall5
        citation = 1.0 if empty_ok else 0.0
    elif case.match == "all":
        recall5 = 1.0 if expected and expected.issubset(set(ranked[:5])) else 0.0
        recall1 = 1.0 if expected and expected.issubset(set(ranked[:1])) else 0.0
        rr = reciprocal_rank(hits)
        ndcg = ndcg_at_k(relevances, 5)
        citation = recall5
    else:
        recall1 = recall_at_k(hits, 1)
        recall5 = recall_at_k(hits, 5)
        rr = reciprocal_rank(hits)
        ndcg = ndcg_at_k(relevances, 5)
        citation = recall5
    snippets_ok = True
    haystack = " ".join(texts[:5]).lower()
    for snip in case.required_snippets:
        if snip.lower() not in haystack:
            snippets_ok = False
            break
    if case.expect_empty:
        snippets_ok = True
    return {
        "id": case.id,
        "category": case.category,
        "recall@1": recall1,
        "recall@5": recall5,
        "rr": round(rr, 3),
        "ndcg@5": round(ndcg, 3),
        "citation_ok": 1.0 if citation and snippets_ok else 0.0,
        "ranked": [list(item) for item in ranked[:5]],
        "found": [list(item) for item in found],
    }


async def run_eval(
    db: AsyncSession,
    dataset: EvalDataset | None = None,
    *,
    allow_semantic: bool = False,
) -> dict:
    dataset = dataset or load_dataset()
    missing = dataset.validate_coverage()
    if missing:
        raise ValueError(f"categorias ausentes: {missing}")
    corpus_version, _ = await compute_corpus_version(db)
    _clear_legal_context_cache()
    per_case: list[dict] = []
    latencies: list[float] = []
    for case in dataset.cases:
        started = time.perf_counter()
        chunks = await retrieve(
            db,
            case.question,
            top_k=5,
            allow_semantic=allow_semantic,
            allow_llm_rerank=False,
        )
        latencies.append((time.perf_counter() - started) * 1000)
        ranked = [_key(c.law_number, c.article or "") for c in chunks]
        texts = [c.text for c in chunks]
        per_case.append(_score_case(case, ranked, texts))

    def _avg(key: str) -> float:
        return round(sum(c[key] for c in per_case) / len(per_case), 3)

    by_cat: dict[str, list[float]] = {}
    for row in per_case:
        by_cat.setdefault(row["category"], []).append(row["recall@5"])
    return {
        "dataset_version": dataset.version,
        "corpus_version": corpus_version,
        "curator": dataset.curator,
        "legal_review": dataset.legal_review,
        "n_cases": len(per_case),
        "recall@1": _avg("recall@1"),
        "recall@5": _avg("recall@5"),
        "mrr": _avg("rr"),
        "ndcg@5": _avg("ndcg@5"),
        "citation_rate": _avg("citation_ok"),
        "recall@5_por_categoria": {
            cat: round(sum(vals) / len(vals), 3) for cat, vals in sorted(by_cat.items())
        },
        "latency_ms_p50": round(percentile(latencies, 50), 1),
        "latency_ms_p95": round(percentile(latencies, 95), 1),
        "cost_usd": 0.0,
        "provider_errors": 0,
        "cases": per_case,
    }


def category_scores(summary: dict) -> dict[str, float]:
    scores = dict(summary.get("recall@5_por_categoria") or {})
    scores["recall@5"] = float(summary.get("recall@5") or 0)
    scores["recall@1"] = float(summary.get("recall@1") or 0)
    scores["mrr"] = float(summary.get("mrr") or 0)
    return scores


def write_baseline(summary: dict, path: Path) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
