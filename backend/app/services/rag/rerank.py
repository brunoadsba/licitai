"""
Rerank determinístico do RAG (Fase R1 — plano rag-moderno-2026-09-18).

Recuperar muito, entregar pouco: o retriever busca ~20 candidatos por backend
e este módulo reordena para os top-k finais sem IO/LLM/rede (puro Python).

Sinais (pesos calibrados no harness `test_rag_recall.py`):
- posição RRF original (0.5): não jogar fora o que a fusão já ordenou;
- overlap de termos com boundary (0.25 por termo, teto 1.0);
- bônus regime (0.30): query 13.303/RILC/estatal casa com chunk 13.303/RILC e
  vice-versa; transversal (TCU/AGU/CGU) neutro em qualquer regime;
- bônus artigo (0.20): nº do artigo da query presente no chunk.
"""

from __future__ import annotations

import re
import unicodedata

_RILC_RE = re.compile(r"RILC|13\.303|estatal|estatais|CODEBA|companhia\s+de\s+docas", re.IGNORECASE)
_14133_RE = re.compile(r"14\.133|preg[aã]o|entes\s+federativos", re.IGNORECASE)
_TRANSVERSAL_RE = re.compile(r"TCU|AGU|CGU|s[úu]mula|ac[óo]rd[ãa]o", re.IGNORECASE)
_ART_RE = re.compile(r"\bart\.?\s*(\d+)(?!\d)", re.IGNORECASE)

REGIME_WEIGHT = 0.30
ARTICLE_WEIGHT = 0.20


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def detect_query_regime(query: str) -> str | None:
    q = query or ""
    rilc = bool(_RILC_RE.search(q))
    fed = bool(_14133_RE.search(q))
    if rilc and not fed:
        return "13.303"
    if fed and not rilc:
        return "14.133"
    return None


def chunk_regime(row: dict) -> str | None:
    blob = f"{row.get('law_number', '')} {row.get('law_title', '')}"
    if _TRANSVERSAL_RE.search(blob):
        return "transversal"
    if _RILC_RE.search(blob):
        return "13.303"
    if _14133_RE.search(blob):
        return "14.133"
    return None


def _query_terms(query: str) -> list[str]:
    return [t for t in _normalize(query).split() if len(t) >= 4]


def _article_numbers(text: str) -> set[str]:
    return {m.group(1) for m in _ART_RE.finditer(text or "")}


def heuristic_rerank(query: str, rows: list[dict]) -> list[dict]:
    """Reordena candidatos; cada linha ganha `rerank_score` (maior = melhor)."""
    if not rows:
        return []
    terms = _query_terms(query)
    q_regime = detect_query_regime(query)
    q_arts = _article_numbers(query)
    rescored: list[dict] = []
    for pos, row in enumerate(rows):
        base = 0.5 / (60 + pos + 1)
        haystack = _normalize(
            f"{row.get('chunk_text', '')} {row.get('article', '')} "
            f"{row.get('law_number', '')} {row.get('section', '')}"
        )
        overlap = sum(1 for t in terms if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", haystack))
        overlap_score = min(1.0, 0.25 * overlap)
        regime_bonus = 0.0
        if q_regime:
            c_regime = chunk_regime(row)
            if c_regime == q_regime:
                regime_bonus = REGIME_WEIGHT
        article_bonus = 0.0
        if q_arts and q_arts & _article_numbers(
            f"{row.get('article', '')} {row.get('chunk_text', '')}"
        ):
            article_bonus = ARTICLE_WEIGHT
        out = dict(row)
        out["rerank_score"] = base + overlap_score + regime_bonus + article_bonus
        rescored.append(out)
    rescored.sort(key=lambda r: r["rerank_score"], reverse=True)
    return rescored


_RERANK_SYSTEM = (
    "Você ordena trechos jurídicos por relevância para a consulta. "
    "Responda SOMENTE JSON: {\"scores\": [{\"i\": <índice>, \"s\": <0-2>}]}. "
    "2 = trata exatamente do tema; 1 = tangencial; 0 = irrelevante."
)


async def llm_rerank(llm, query: str, rows: list[dict], top_k: int = 5) -> list[dict]:
    """Rerank opt-in via LLM (R3) sobre os top-10 heurísticos.

    Fail-open: qualquer falha devolve as linhas na ordem de entrada.
    O chamador garante a trava de privacidade (sigiloso nunca vai a cloud).
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    if not rows or llm is None:
        return rows
    cands = rows[:10]
    numbered = "\n".join(
        f"[{i}] {r.get('law_number', '')} {r.get('article', '')}: "
        f"{(r.get('chunk_text', '') or '')[:500]}"
        for i, r in enumerate(cands)
    )
    try:
        raw = await llm.generate(_RERANK_SYSTEM, f"Consulta: {query[:500]}\n{numbered}")
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return rows
        payload = json.loads(raw[start : end + 1])
        scores = payload.get("scores", []) if isinstance(payload, dict) else []
        table = {
            int(e["i"]): float(e.get("s", 0))
            for e in scores
            if isinstance(e, dict) and "i" in e
        }
        if not table:
            return rows
        ranked = sorted(
            range(len(cands)),
            key=lambda i: (-table.get(i, 0.0), i),
        )
        out = [dict(cands[i]) for i in ranked[:top_k]]
        out += [dict(r) for r in rows[10:]]
        return out
    except Exception:
        logger.warning("llm_rerank falhou; mantendo ordem heurística", exc_info=True)
        return rows
