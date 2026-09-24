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


def traces_from_corrections(corrections) -> list[str]:
    """Uma linha por correção: id curto, fundamento e DE."""
    lines: list[str] = []
    for item in corrections or []:
        cid = str(getattr(item, "id", "") or "")[:8]
        basis = (getattr(item, "legal_basis", None) or "sem fundamento").strip()
        de = (getattr(item, "original_text", None) or "").strip().replace("\n", " ")
        if len(de) > 80:
            de = de[:77] + "..."
        if cid:
            lines.append(f"{cid} · {basis} · DE: {de or '—'}")
    return lines


def append_parecer_origins(
    opinion: str,
    correction_ids: list[str],
    retrieval_run_ids: list[str],
    correction_traces: list[str] | None = None,
) -> str:
    """Acrescenta rodapé auditável sem alterar o texto do parecer."""
    parts = [(opinion or "").rstrip()]
    traces = _uniq(correction_traces or [], limit=12)
    if traces:
        parts.append("Rastro das correções:")
        parts.extend(f"- {line}" for line in traces)
    corrections = _uniq(correction_ids)
    runs = _uniq(retrieval_run_ids)
    if corrections:
        parts.append("Fontes do parecer: correções " + ", ".join(corrections) + ".")
    if runs:
        parts.append("Recuperações: " + ", ".join(runs) + ".")
    return "\n".join(p for p in parts if p)
