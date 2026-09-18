"""Avaliação RAG do piloto — roda o harness R0 e imprime a tabela.

Uso: PYTHONPATH=backend python3 backend/scripts/eval_rag.py
Sem rede/LLM (provedor fake). Saída: backend/rag_eval_baseline.json + tabela.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_rag_recall import evaluate_retriever  # noqa: E402


def main() -> int:
    summary = evaluate_retriever()
    print(f"queries={summary['n_queries']}  recall@5={summary['recall@5']}  mrr={summary['mrr']}")
    for q in summary["queries"]:
        top3 = " | ".join(f"{law} {art}" for law, art in q["ranked"][:3])
        flag = "OK " if q["recall@5"] else "MISS"
        print(f"[{flag}] r@5={q['recall@5']} rr={q['rr']:.2f} :: {q['query']}\n      top3: {top3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
