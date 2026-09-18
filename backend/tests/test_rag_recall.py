"""
Harness R0 — Recall@k / MRR do retriever RAG (plano rag-moderno-2026-09-18).

Corpus de 12 chunks em 4 fontes com colisão proposital ("Art. 6º" em duas leis,
"garantia de execução" em duas leis). O provedor semântico fake devolve o vetor
do chunk DISTRATOR (simula confusão de embedding); o textual (FTS) carrega o
sinal correto. R1 (rerank + filtro regime) deve subir MRR sem regredir Recall.

Roda sem rede/LLM: `pytest backend/tests/test_rag_recall.py -q`.
Baseline registrado em `backend/rag_eval_baseline.json` a cada run.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.services.rag.loader import build_fts_index
from app.services.rag.retriever import _clear_legal_context_cache, retrieve

DIM = 12

# (law_number, law_title, article, section, chunk_text)
CORPUS: list[tuple[str, str, str, str, str]] = [
    ("Lei 14.133/2021", "Licitações", "Art. 6º", "",
     "definição de termo de referência, projeto básico e projeto executivo nas licitações"),
    ("Lei 14.133/2021", "Licitações", "Art. 67", "",
     "garantia de execução contratual nas licitações públicas"),
    ("Lei 14.133/2021", "Licitações", "Art. 28", "",
     "instruções de segurança do trabalho nos editais"),
    ("Lei 14.133/2021", "Licitações", "Art. 11", "",
     "objetivos do processo licitatório e governança das contratações"),
    ("Lei 13.303/2016", "Estatais", "Art. 32", "",
     "regulamento interno de licitações das empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 40", "",
     "garantia de execução nos contratos das empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 29", "",
     "termo de referência simplificado nas empresas estatais"),
    ("Lei 13.303/2016", "Estatais", "Art. 31", "",
     "princípios da publicidade e julgamento objetivo nas estatais"),
    ("RILC CODEBA", "Regulamento", "Art. 6º", "",
     "termo de referência nas contratações da companhia de docas"),
    ("RILC CODEBA", "Regulamento", "Art. 12", "",
     "prazo de vigência de vinte e quatro meses e prorrogação contratual"),
    ("TCU", "Jurisprudência", "Súmula 247", "",
     "parcelamento do objeto para ampla competitividade nas licitações"),
    ("TCU", "Jurisprudência", "Acórdão 1214/2013", "",
     "planejamento e pesquisa de preços nas contratações públicas"),
]

# (query, índice esperado no CORPUS, índice do distrator semântico)
QUERIES: list[tuple[str, int, int]] = [
    ("termo de referência art. 6 RILC companhia", 8, 0),
    ("garantia de execução estatal", 5, 1),
    ("parcelamento do objeto competitividade", 10, 0),
    ("prazo de vigência vinte e quatro meses prorrogação", 9, 1),
    ("regulamento interno de licitações estatais", 4, 0),
    ("projeto básico termo de referência", 0, 0),
]

BASELINE_PATH = Path(__file__).resolve().parents[1] / "rag_eval_baseline.json"


def _one_hot(i: int) -> list[float]:
    return [1.0 if j == i else 0.0 for j in range(DIM)]


class _FakeProvider:
    provider_name = "fake-recall"
    model_name = "fake"

    async def embed(self, text: str) -> list[float]:
        for query, _exp, dist in QUERIES:
            if text.strip().lower() == query:
                return _one_hot(dist)
        return _one_hot(0)

    async def health_check(self) -> bool:
        return True


def _run(coro):
    return asyncio.run(coro)


async def _seed() -> async_sessionmaker:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    docs: dict[str, object] = {}
    async with Session() as db:
        for law, title, article, section, text in CORPUS:
            if law not in docs:
                doc = LegalDocument(law_number=law, law_title=title)
                db.add(doc)
                await db.flush()
                docs[law] = doc
            assert not isinstance(docs[law], str)
            db.add(LegalChunk(
                legal_document_id=docs[law].id,  # type: ignore[attr-defined]
                chunk_index=0, article=article, section=section,
                chunk_text=text, embedding=json.dumps(_one_hot(CORPUS.index(
                    (law, title, article, section, text)))),
            ))
        await build_fts_index(db)
        await db.commit()
    return Session


def _expected_key(idx: int) -> tuple[str, str]:
    law, _t, art, _s, _x = CORPUS[idx]
    return (law, art)


def _recall_at_k(ranked: list[tuple[str, str]], expected: tuple[str, str], k: int) -> float:
    return 1.0 if expected in ranked[:k] else 0.0


def _reciprocal_rank(ranked: list[tuple[str, str]], expected: tuple[str, str]) -> float:
    for i, key in enumerate(ranked):
        if key == expected:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_retriever() -> dict:
    """Roda as 6 queries e devolve Recall@5, Recall@10, MRR + por-query."""
    import app.services.rag.retriever as retriever_module

    orig = retriever_module.get_embeddings_provider
    retriever_module.get_embeddings_provider = lambda: _FakeProvider()  # type: ignore[assignment]
    try:
        async def _cenario():
            _clear_legal_context_cache()
            Session = await _seed()
            out = []
            async with Session() as db:
                for query, exp_idx, _d in QUERIES:
                    chunks = await retrieve(db, query, top_k=10)
                    ranked = [(c.law_number, c.article) for c in chunks]
                    out.append({
                        "query": query,
                        "expected": list(_expected_key(exp_idx)),
                        "ranked": [list(k) for k in ranked],
                        "recall@5": _recall_at_k(ranked, _expected_key(exp_idx), 5),
                        "rr": _reciprocal_rank(ranked, _expected_key(exp_idx)),
                    })
            return out
        per_query = _run(_cenario())
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]
    n = len(per_query)
    summary = {
        "n_queries": n,
        "recall@5": round(sum(q["recall@5"] for q in per_query) / n, 3),
        "mrr": round(sum(q["rr"] for q in per_query) / n, 3),
        "queries": per_query,
    }
    BASELINE_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def test_rag_recall_baseline():
    summary = evaluate_retriever()
    # Pisos R1 (18/09, com rerank heurístico): recall@5=1.0, mrr=1.0.
    # Qualquer queda abaixo = regressão do rerank/RRF.
    assert summary["recall@5"] >= 1.0, summary
    assert summary["mrr"] >= 0.9, summary
    # Colisão Art. 6º: query RILC deve trazer RILC Art. 6º no top-5.
    rilc = next(q for q in summary["queries"] if "RILC" in q["query"])
    assert rilc["recall@5"] == 1.0, rilc
