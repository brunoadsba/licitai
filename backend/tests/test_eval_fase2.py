"""Fase 2: contrato do conjunto, métricas e regressão da baseline."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument  # noqa: F401
from app.models.retrieval import RetrievalRun  # noqa: F401
from eval.metrics import ndcg_at_k, reciprocal_rank, regression_breaches
from eval.runner import category_scores, load_dataset, run_eval
from eval.schema import CATEGORIES
from eval.seed import seed_eval_corpus


def test_dataset_cobre_categorias_e_seguranca():
    dataset = load_dataset()
    assert dataset.validate_coverage() == []
    assert dataset.legal_review in {"pendente", "aprovada"}
    ids = {c.id for c in dataset.cases}
    assert "inj-001" in ids
    assert "auth-001" in ids
    assert {c.category for c in dataset.cases} == set(CATEGORIES)


def test_metricas_basicas():
    assert reciprocal_rank([False, True, False]) == 0.5
    assert ndcg_at_k([1.0, 0.0, 0.0], 5) == 1.0
    assert regression_breaches({"a": 0.90}, {"a": 0.95}, 2.0)
    assert not regression_breaches({"a": 0.94}, {"a": 0.95}, 2.0)


def test_eval_semente_sqlite_bate_baseline_minima():
    async def _cenario():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            await seed_eval_corpus(db)
            return await run_eval(db, allow_semantic=False)

    summary = asyncio.run(_cenario())
    assert summary["n_cases"] == 14
    assert summary["corpus_version"]
    assert summary["recall@5"] >= 0.9
    scores = category_scores(summary)
    for cat in CATEGORIES:
        assert cat in scores
        assert scores[cat] >= 0.0


def test_regressao_acima_de_dois_pp_falha():
    atual = {"recall@5": 0.80, "localizacao": 0.50}
    base = {"recall@5": 0.90, "localizacao": 1.0}
    breaches = regression_breaches(atual, base, 2.0)
    assert any("recall@5" in b for b in breaches)
    assert any("localizacao" in b for b in breaches)
