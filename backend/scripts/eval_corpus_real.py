"""Avaliação Fase 2 no PostgreSQL (ou SQLite de CI).

Uso:
  PYTHONPATH=backend python scripts/eval_corpus_real.py --seed --write-baseline
  PYTHONPATH=backend python scripts/eval_corpus_real.py --check-baseline
  PYTHONPATH=backend python scripts/eval_corpus_real.py --piloto
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database import Base
from eval.metrics import regression_breaches
from eval.runner import (
    BASELINE_CI_PATH,
    category_scores,
    load_dataset,
    run_eval,
    write_baseline,
)
from eval.seed import seed_eval_corpus


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Avaliação curada Fase 2")
    p.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    p.add_argument("--seed", action="store_true", help="Semeia corpus mínimo")
    p.add_argument("--piloto", action="store_true", help="Usa o banco já populado")
    p.add_argument("--write-baseline", action="store_true")
    p.add_argument("--check-baseline", action="store_true")
    p.add_argument("--baseline", type=Path, default=BASELINE_CI_PATH)
    p.add_argument("--semantic", action="store_true")
    return p.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    url = args.database_url
    if not url:
        raise SystemExit("DATABASE_URL ou --database-url é obrigatório")
    engine = create_async_engine(url)
    try:
        if args.seed:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            if args.seed:
                await seed_eval_corpus(db)
            return await run_eval(db, load_dataset(), allow_semantic=args.semantic)
    finally:
        await engine.dispose()


def main() -> int:
    args = _parse()
    summary = asyncio.run(_run(args))
    print(
        f"n={summary['n_cases']} r@1={summary['recall@1']} "
        f"r@5={summary['recall@5']} mrr={summary['mrr']} "
        f"corpus={summary['corpus_version'][:12]}"
    )
    for cat, val in summary["recall@5_por_categoria"].items():
        print(f"  {cat}: {val}")
    if args.write_baseline:
        write_baseline(summary, args.baseline)
        print(f"baseline gravada em {args.baseline}")
    if args.check_baseline:
        if not args.baseline.exists():
            print(f"baseline ausente: {args.baseline}", file=sys.stderr)
            return 1
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        dataset = load_dataset()
        breaches = regression_breaches(
            category_scores(summary),
            category_scores(base),
            dataset.tolerance_pp,
        )
        if breaches:
            print("REGRESSÃO:", file=sys.stderr)
            for item in breaches:
                print(f"  {item}", file=sys.stderr)
            return 1
        print("baseline ok (tolerância "
              f"{dataset.tolerance_pp}pp)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
