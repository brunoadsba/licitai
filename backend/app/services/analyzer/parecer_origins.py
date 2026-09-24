"""Anexa ao parecer os IDs das correções e recuperações de origem."""

from __future__ import annotations


def _uniq(values: list[str], limit: int = 20) -> list[str]:
    seen: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.append(value)
        if len(seen) >= limit:
            break
    return seen


def append_parecer_origins(
    opinion: str,
    correction_ids: list[str],
    retrieval_run_ids: list[str],
) -> str:
    """Acrescenta rodapé auditável sem alterar o texto do parecer."""
    parts = [(opinion or "").rstrip()]
    corrections = _uniq(correction_ids)
    runs = _uniq(retrieval_run_ids)
    if corrections:
        parts.append("Fontes do parecer: correções " + ", ".join(corrections) + ".")
    if runs:
        parts.append("Recuperações: " + ", ".join(runs) + ".")
    return "\n".join(p for p in parts if p)
