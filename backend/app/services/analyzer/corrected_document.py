"""Monta TR HTML com correções SEI-aplicáveis (aprovada|ajustada)."""

from __future__ import annotations

import html
import re
from typing import Iterable

from app.services.analyzer.grounding import _normalize

SEI_APPLICABLE_STATUSES = frozenset({"aprovada", "ajustada"})


def _find_original_span(haystack: str, needle: str) -> tuple[int, int] | None:
    """Localiza needle no haystack (exato ou com whitespace/acentos normalizados)."""
    if not needle or not haystack:
        return None
    if needle in haystack:
        start = haystack.index(needle)
        return start, start + len(needle)

    norm_h = _normalize(haystack)
    norm_n = _normalize(needle)
    if not norm_n or norm_n not in norm_h:
        return None

    # Regex: espaços flexíveis entre tokens do needle original
    tokens = [t for t in re.split(r"\s+", needle.strip()) if t]
    if not tokens:
        return None
    parts = [re.escape(t) for t in tokens]
    pattern = r"\s+".join(parts)
    m = re.search(pattern, haystack, flags=re.IGNORECASE)
    if m:
        return m.start(), m.end()

    # Fallback: varrer janelas do haystack com mesmo tamanho normalizado
    target = norm_n
    # Construir acumulado normalizado com ponteiros
    acc = []
    positions: list[int] = []
    for idx, ch in enumerate(haystack):
        nch = _normalize(ch)
        if not nch:
            continue
        if nch == " ":
            if acc and acc[-1] == " ":
                continue
            acc.append(" ")
            positions.append(idx)
        else:
            for c in nch:
                acc.append(c)
                positions.append(idx)
    joined = "".join(acc)
    pos = joined.find(target)
    if pos < 0:
        return None
    start_orig = positions[pos]
    end_pos = pos + len(target) - 1
    end_orig = positions[end_pos] + 1
    return start_orig, end_orig


def apply_sei_corrections_to_text(
    content: str, corrections: Iterable
) -> tuple[str, list[dict], list[dict]]:
    """
    Aplica replaces DE→PARA (aprovada|ajustada).
    Retorna (texto, applied[{id}], skipped[{id, reason}]).
    """
    text = content or ""
    applied: list[dict] = []
    skipped: list[dict] = []
    for c in corrections:
        status = getattr(c, "review_status", None)
        if status not in SEI_APPLICABLE_STATUSES:
            continue
        cid = getattr(c, "id", None)
        original = getattr(c, "original_text", None) or ""
        suggested = getattr(c, "suggested_text", None) or ""
        if not original or not suggested:
            skipped.append({"correction_id": cid, "reason": "empty_texts"})
            continue
        span = _find_original_span(text, original)
        if not span:
            skipped.append({"correction_id": cid, "reason": "not_found"})
            continue
        start, end = span
        text = text[:start] + suggested + text[end:]
        applied.append({"correction_id": cid})
    return text, applied, skipped


def build_corrected_html(
    *,
    filename: str,
    items: list,
    corrections_by_item: dict,
) -> tuple[str, list[dict], list[dict]]:
    """HTML simples (h1/h2/p). Retorna (html, applied, skipped)."""
    parts: list[str] = [f"<h1>{html.escape(filename.upper())}</h1>\n"]
    all_applied: list[dict] = []
    all_skipped: list[dict] = []
    for item in sorted(items, key=lambda i: getattr(i, "item_order", 0) or 0):
        item_id = getattr(item, "id", None)
        corrs = corrections_by_item.get(item_id, []) if item_id else []
        content, applied, skipped = apply_sei_corrections_to_text(
            getattr(item, "content", "") or "", corrs
        )
        all_applied.extend(applied)
        all_skipped.extend(skipped)
        number = html.escape(str(getattr(item, "item_number", "") or ""))
        title = html.escape(str(getattr(item, "title", "") or ""))
        heading = f"{number} {title}".strip()
        parts.append(f"<h2>{heading}</h2>\n")
        body = html.escape(content).replace("\n", "<br/>")
        parts.append(f"<p>{body}</p>\n")
    return "".join(parts), all_applied, all_skipped


def build_sei_pack_text(
    *,
    document_name: str,
    entries: list[dict],
) -> str:
    """Pacote texto/markdown ordenado para colar no SEI."""
    lines = [
        f"# Pacote SEI — {document_name}",
        "",
        "Somente correções aprovadas ou ajustadas.",
        "",
    ]
    if not entries:
        lines.append("_Nenhuma correção aprovada/ajustada ainda._")
        return "\n".join(lines)

    for i, e in enumerate(entries, start=1):
        lines.append(f"## {i}. Item {e['item_number']}")
        if e.get("title"):
            lines.append(f"**Título:** {e['title']}")
        lines.append("")
        lines.append("**PARA (colar no SEI):**")
        lines.append(e["suggested_text"])
        lines.append("")
        if e.get("justification"):
            lines.append("**Justificativa:**")
            lines.append(e["justification"])
            lines.append("")
        if e.get("legal_basis"):
            lines.append(f"**Base legal:** {e['legal_basis']}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
