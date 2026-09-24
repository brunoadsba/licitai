"""Fase 5: consulta por artigo, hierarquia e cache por corpus/classificação."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.legal import LegalChunk, LegalDocument
from app.models.legal_versioned import LegalProvision, LegalVersion, LegalWork
from app.models.retrieval import RetrievalRun  # noqa: F401
from app.services.rag.article_query import (
    article_like,
    extract_article_ref,
    filter_weak_fts_hits,
)
from app.services.rag.hierarchy import (
    DEFAULT_TOKEN_BUDGET,
    expand_hierarchical,
    provision_path_from_article,
)
from app.services.rag.loader import build_fts_index
from app.services.rag.retriever import (
    RetrievedChunk,
    _clear_legal_context_cache,
    _cache_stats,
    retrieve,
)


def _run(coro):
    return asyncio.run(coro)


def test_extract_article_ref():
    assert extract_article_ref("o que diz o art. 37") == "37"
    assert extract_article_ref("Artigo 6º da lei") == "6"
    assert article_like("artigo 75") == "%75%"
    assert extract_article_ref("prazo de pagamento") is None
    assert provision_path_from_article("Art. 6º") == "art.6"
    weak = filter_weak_fts_hits(
        "xyzzyplugh casamento 1639 comunhao",
        [{"chunk_text": "formalizar a comunhão de esforços", "article": "Art. 278"}],
    )
    assert weak == []
    strong = filter_weak_fts_hits(
        "legalidade impessoalidade moralidade ignore senha",
        [{"chunk_text": "legalidade, impessoalidade e moralidade", "article": "Art. 5º"}],
    )
    assert strong


async def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_retrieve_artigo_direto():
    _clear_legal_context_cache()

    async def _cenario():
        Session = await _session()
        async with Session() as db:
            doc = LegalDocument(law_number="Lei 14.133/2021", law_title="Licitações")
            db.add(doc)
            await db.flush()
            db.add_all(
                [
                    LegalChunk(
                        legal_document_id=doc.id,
                        chunk_index=0,
                        article="Art. 37",
                        chunk_text="Vedado exigir documentação além da prevista.",
                    ),
                    LegalChunk(
                        legal_document_id=doc.id,
                        chunk_index=1,
                        article="Art. 6º",
                        chunk_text="Definições do termo de referência.",
                    ),
                ]
            )
            await build_fts_index(db)
            await db.commit()
            return await retrieve(db, "artigo 37 da lei de licitações", top_k=2)

    chunks = _run(_cenario())
    assert any(c.article == "Art. 37" for c in chunks)


def test_cache_separa_classificacao():
    _clear_legal_context_cache()

    async def _cenario():
        Session = await _session()
        async with Session() as db:
            doc = LegalDocument(law_number="Lei 14.133/2021", law_title="Licitações")
            db.add(doc)
            await db.flush()
            db.add(
                LegalChunk(
                    legal_document_id=doc.id,
                    chunk_index=0,
                    article="Art. 6º",
                    chunk_text="Garantia de execução exigida no edital.",
                )
            )
            await build_fts_index(db)
            await db.commit()
            first = await retrieve(
                db, "garantia de execução", top_k=1, classification="publico"
            )
            second = await retrieve(
                db, "garantia de execução", top_k=1, classification="interno"
            )
            third = await retrieve(
                db, "garantia de execução", top_k=1, classification="publico"
            )
            return first, second, third

    first, second, third = _run(_cenario())
    assert first and second and third
    assert first[0].text == third[0].text
    assert _cache_stats["hit"] >= 1
    assert _cache_stats["miss"] >= 2


def test_hierarquia_nao_trunca_artigo():
    async def _cenario():
        Session = await _session()
        async with Session() as db:
            work = LegalWork(law_number="Lei 14.133/2021", title="Licitações")
            db.add(work)
            await db.flush()
            version = LegalVersion(
                work_id=work.id, content_hash="abc", status="published"
            )
            db.add(version)
            await db.flush()
            caput = LegalProvision(
                version_id=version.id,
                work_id=work.id,
                path="art.6",
                article="Art. 6º",
                canonical_text="Caput do art. 6º com definição.",
                status="vigente",
                provision_hash="h1",
            )
            db.add(caput)
            await db.flush()
            para = LegalProvision(
                version_id=version.id,
                work_id=work.id,
                parent_id=caput.id,
                path="art.6/par.1",
                article="Art. 6º",
                paragraph="1",
                canonical_text="§ 1º Exceção do caput.",
                status="vigente",
                provision_hash="h2",
            )
            db.add(para)
            await db.commit()
            chunk = RetrievedChunk(
                id=str(uuid.uuid4()),
                law_number="Lei 14.133/2021",
                law_title="Licitações",
                article="Art. 6º",
                section="",
                text="§ 1º Exceção do caput.",
                score=1.0,
            )
            expanded = await expand_hierarchical(db, [chunk], token_budget=DEFAULT_TOKEN_BUDGET)
            return expanded

    expanded = _run(_cenario())
    assert expanded
    assert "Caput do art. 6º" in expanded[0].text
    assert "Exceção do caput" in expanded[0].text


def test_hierarquia_reduz_dispositivos_antes_de_cortar():
    async def _cenario():
        Session = await _session()
        async with Session() as db:
            chunks = [
                RetrievedChunk(
                    id=str(uuid.uuid4()),
                    law_number="Lei 14.133/2021",
                    law_title="Licitações",
                    article=f"Art. {i}",
                    section="",
                    text="x" * 800,
                    score=1.0,
                )
                for i in range(5)
            ]
            return await expand_hierarchical(db, chunks, token_budget=400)

    expanded = _run(_cenario())
    assert 1 <= len(expanded) < 5
    assert all(len(c.text) == 800 for c in expanded)
