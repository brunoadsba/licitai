"""Avaliação de recall/precisão contra golden anotado (modo offline, sem LLM).

Mesma semântica de casamento do `benchmark.py` (substring case-insensitive
sobre o texto das correções), extraída para módulo testável: o script
`benchmark_offline.py` é só IO (golden + banco), a lógica mora aqui.
"""

from __future__ import annotations


def _corrections_text(corrections: list[dict]) -> str:
    return " ".join(
        f"{c.get('problem', '')} {c.get('situation', '')} "
        f"{c.get('original_text', '')} {c.get('suggested_text', '')} "
        f"{c.get('justification', '')} {c.get('risk', '')}"
        for c in corrections
    )


def evaluate_golden(
    expected_findings: list[dict],
    corrections: list[dict],
    known_fps: list[dict] | None = None,
) -> dict:
    """Recall sobre achados esperados + tripwire sobre FPs conhecidos.

    `expected_findings`: [{item_number, keyword, ...}].
    `known_fps`: [{keyword, ...}] — cada hit aqui é um FP que voltou.
    """
    text = _corrections_text(corrections)
    hits = sum(
        1 for issue in expected_findings
        if issue.get("keyword", "").lower() in text.lower()
    )
    total = len(expected_findings)
    fp_hits = [
        fp for fp in (known_fps or [])
        if fp.get("keyword", "").lower() in text.lower()
    ]
    return {
        "recall": hits / total if total else 1.0,
        "hits": hits,
        "total": total,
        "fp_hits": len(fp_hits),
        "fp_total": len(known_fps or []),
        "fp_matched": [fp.get("keyword", "") for fp in fp_hits],
    }
