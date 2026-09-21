"""Robustez do RAG: determinismo, fallback, cache, entradas hostis.

Sem rede/LLM. Reusa o seed do harness hard.
"""

from __future__ import annotations

import asyncio

from tests.test_rag_recall import _FakeProvider, _seed
import app.services.rag.retriever as retriever_module
from app.services.rag.backends import _fts_terms
from app.services.rag.retriever import _clear_legal_context_cache, retrieve


def _run(coro):
    return asyncio.run(coro)


def _with_fake():
    orig = retriever_module.get_embeddings_provider
    retriever_module.get_embeddings_provider = lambda: _FakeProvider()  # type: ignore[assignment]
    return orig


async def _query_twice(query: str, top_k: int):
    Session = await _seed()
    async with Session() as db:
        first = await retrieve(db, query, top_k=top_k)
        second = await retrieve(db, query, top_k=top_k)
    return first, second


def test_deterministico_mesma_ordem():
    orig = _with_fake()
    try:
        _clear_legal_context_cache()
        a, b = _run(_query_twice("garantia de execução estatal", 5))
        assert [(c.law_number, c.article) for c in a] == [(c.law_number, c.article) for c in b]
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]


def test_cache_isola_top_k_e_modo():
    orig = _with_fake()
    try:
        async def _cenario():
            _clear_legal_context_cache()
            Session = await _seed()
            async with Session() as db:
                cinco = await retrieve(db, "garantia de execução estatal", top_k=5)
                dez = await retrieve(db, "garantia de execução estatal", top_k=10)
                assert len(cinco) == 5
                assert len(dez) == 10
                assert [c.id for c in dez[:5]] == [c.id for c in cinco]
        _run(_cenario())
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]


def test_fallback_textual_quando_semantica_falha():
    class _Quebrado(_FakeProvider):
        async def embed(self, text: str) -> list[float]:
            raise RuntimeError("indisponível")

    orig = retriever_module.get_embeddings_provider
    retriever_module.get_embeddings_provider = lambda: _Quebrado()  # type: ignore[assignment]
    try:
        async def _cenario():
            _clear_legal_context_cache()
            Session = await _seed()
            async with Session() as db:
                chunks = await retrieve(db, "parcelamento objeto competitividade", top_k=5)
                assert any(c.article == "Súmula 247" for c in chunks)
        _run(_cenario())
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]


def test_query_vazia_e_hostil_nao_quebram():
    orig = _with_fake()
    try:
        async def _cenario():
            _clear_legal_context_cache()
            Session = await _seed()
            async with Session() as db:
                assert await retrieve(db, "   ", top_k=5) == []
                fora = await retrieve(db, "requisitos de computação quântica", top_k=5)
                assert isinstance(fora, list) and len(fora) <= 5
                inj = await retrieve(db, '" OR 1=1 --', top_k=5)
                assert isinstance(inj, list)
        _run(_cenario())
    finally:
        retriever_module.get_embeddings_provider = orig  # type: ignore[assignment]


def test_fts_remove_stopwords_e_prefixa():
    terms = _fts_terms("fiscalização estatal por preposto")
    blob = " ".join(terms)
    assert "por" not in [t.strip('"') for t in terms]
    assert any(t.endswith("*") for t in terms)
    assert _fts_terms("   ") != []
