#!/usr/bin/env python3
"""
Promove stubs de thumbs-down (e2e/golden/feedback/) para fixtures golden candidatas.

Uso:
  PYTHONPATH=backend python backend/scripts/promote_feedback.py --list
  PYTHONPATH=backend python backend/scripts/promote_feedback.py --stub PATH --dry-run
  PYTHONPATH=backend python backend/scripts/promote_feedback.py --stub PATH --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FEEDBACK_DIR = REPO / "e2e" / "golden" / "feedback"
GOLDEN_DIR = REPO / "e2e" / "golden"


def _next_tr_id() -> str:
    existing = sorted(GOLDEN_DIR.glob("tr_*.json"))
    nums = []
    for p in existing:
        try:
            nums.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    n = max(nums, default=0) + 1
    return f"tr_{n:03d}"


def list_stubs() -> list[Path]:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(FEEDBACK_DIR.glob("thumbs_down_*.json"))


def promote(stub_path: Path, *, apply: bool) -> Path:
    data = json.loads(stub_path.read_text(encoding="utf-8"))
    tr_id = _next_tr_id()
    fixture = {
        "id": tr_id,
        "descricao": (
            f"Promovido de feedback chat message_id={data.get('message_id')} "
            f"(curadoria humana pendente)"
        ),
        "itens": [
            {
                "item_number": "1.0",
                "title": "CONTEUDO_ASSISTENTE_PARA_CURADORIA",
                "content": (data.get("assistant_content") or "")[:2000],
            }
        ],
        "expected_checklist": [],
        "expected_findings": [],
        "source_feedback": {
            "stub": stub_path.name,
            "comment": data.get("comment"),
            "conversation_id": data.get("conversation_id"),
        },
        "status": "needs_human_curation",
    }
    out = GOLDEN_DIR / f"{tr_id}.json"
    if apply:
        out.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        stub_path.rename(FEEDBACK_DIR / f"promoted_{stub_path.name}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--stub", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.list:
        stubs = list_stubs()
        for s in stubs:
            print(s)
        print(f"total={len(stubs)}")
        return 0

    if not args.stub:
        parser.error("informe --stub PATH ou --list")

    stub = args.stub if args.stub.is_absolute() else (REPO / args.stub)
    if not stub.exists():
        print(f"stub não encontrado: {stub}", file=sys.stderr)
        return 1

    apply = bool(args.apply) and not args.dry_run
    out = promote(stub, apply=apply)
    print(("wrote " if apply else "would write ") + str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
