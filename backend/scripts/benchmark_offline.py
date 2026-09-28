"""Benchmark offline do recall em TR real (Fase 3) — zero chamadas LLM.

Compara as correções JÁ persistidas de uma análise contra o golden anotado
(`e2e/golden/real/tr_pabx.json`) e grava `docs/ops/recall-tr-real-2026-09.md`.

Uso:
    cd backend && PYTHONPATH=. python scripts/benchmark_offline.py \
        --golden ../e2e/golden/real/tr_pabx.json \
        --analysis-id 8cdafd60-3720-401d-b090-efc83c154af5

Lê DATABASE_URL do ambiente (aponta p/ o Postgres piloto).
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.analysis import Correction  # noqa: E402
from app.services.analyzer.recall_eval import evaluate_golden  # noqa: E402

OUT = Path(__file__).resolve().parent.parent.parent / "docs" / "ops" / "recall-tr-real-2026-09.md"

_HONEST = (
    "\n## Leitura honesta\n\n"
    "Golden v2 (3 TPs humanos 16/09 + 18 tripwires; carimbo dos 17 pendentes\n"
    "feito em 28/09, 0 aprovar / 17 rejeitar). Recall v1 0,25 (3/12) é harness\n"
    "arquivado, não medida do v2. Re-medir exige análise no Postgres.\n"
)


def _upsert_report(previous: str, analysis_id: str, section: str, header: str) -> str:
    """Substitui a seção deste analysis_id. Não acumula rodadas."""
    if "Recall em TR real" not in previous:
        previous = header + _HONEST
    pattern = re.compile(
        rf"\n## [^\n]*\(`{re.escape(analysis_id)}`\)\n.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    block = "\n" + section.strip() + "\n"
    if pattern.search(previous):
        return pattern.sub(block, previous, count=1).rstrip() + "\n"
    return previous.rstrip() + block


async def _load_corrections(db, analysis_id: str) -> list[dict]:
    rows = (
        await db.execute(
            select(Correction).where(Correction.analysis_id == analysis_id)
        )
    ).scalars().all()
    return [
        {
            "problem": c.problem or "",
            "situation": c.situation or "",
            "original_text": c.original_text or "",
            "suggested_text": c.suggested_text or "",
            "justification": c.justification or "",
            "risk": c.risk or "",
        }
        for c in rows
    ]


async def main() -> None:
    p = argparse.ArgumentParser(description="Recall offline em TR real (sem LLM)")
    p.add_argument("--golden", required=True)
    p.add_argument("--analysis-id", required=True)
    p.add_argument("--label", default="")
    args = p.parse_args()

    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL não definido")

    engine = create_async_engine(url)
    try:
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            corrections = await _load_corrections(db, args.analysis_id)
    finally:
        await engine.dispose()

    result = evaluate_golden(
        golden.get("expected_findings", []),
        corrections,
        golden.get("known_fps", []),
    )
    label = args.label or args.analysis_id[:8]
    print(f"[{label}] correções={len(corrections)} "
          f"recall={result['recall']:.2f} ({result['hits']}/{result['total']}) "
          f"fp={result['fp_hits']}/{result['fp_total']} {result['fp_matched']}")

    if not corrections:
        print("Sem correções: relatório não alterado.")
        return

    header = (
        "# Recall em TR real — 09-ti-pabx-nuvem (28/09/2026)\n\n"
        f"Golden: `{args.golden}` (status: {golden.get('provenance', {}).get('status', '?')})\n"
    )
    section = (
        f"## {label} (`{args.analysis_id}`)\n\n"
        f"- Correções avaliadas: {len(corrections)}\n"
        f"- Recall: **{result['recall']:.2f}** ({result['hits']}/{result['total']})\n"
        f"- FPs conhecidos reincidentes: **{result['fp_hits']}/{result['fp_total']}** {result['fp_matched']}\n"
    )
    previous = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    OUT.write_text(
        _upsert_report(previous, args.analysis_id, section, header),
        encoding="utf-8",
    )
    print(f"Relatório: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
