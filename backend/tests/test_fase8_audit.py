"""Fase 8: dispositivos e pacote de auditoria."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.models.legal_versioned import LegalProvision, LegalVersion, LegalWork
from app.models.retrieval import RetrievalRun  # noqa: F401
from app.services.legal_model.query import list_provisions


def _run(coro):
    return asyncio.run(coro)


async def _session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_list_provisions_vigente_por_padrao():
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
            db.add_all(
                [
                    LegalProvision(
                        version_id=version.id,
                        work_id=work.id,
                        path="art.6",
                        article="Art. 6º",
                        canonical_text="Caput vigente.",
                        status="vigente",
                        provision_hash="h1",
                    ),
                    LegalProvision(
                        version_id=version.id,
                        work_id=work.id,
                        path="art.172",
                        article="Art. 172",
                        canonical_text="Vetado.",
                        status="vetado",
                        provision_hash="h2",
                    ),
                ]
            )
            await db.commit()
            return await list_provisions(db, law_number="Lei 14.133/2021")

    rows = _run(_cenario())
    assert [r.path for r in rows] == ["art.6"]


def test_audit_pack_monta_de_para():
    from app.api.analysis_audit import get_audit_pack

    async def _cenario():
        Session = await _session()
        async with Session() as db:
            doc = Document(
                filename_original="tr.pdf",
                filename_stored=f"{uuid.uuid4()}.pdf",
                file_type="pdf",
                file_size_bytes=1024,
                document_type="tr",
                status="completed",
            )
            db.add(doc)
            await db.flush()
            item = DocumentItem(
                document_id=doc.id,
                item_number="1.1",
                title="Objeto",
                content="texto original",
            )
            db.add(item)
            await db.flush()
            analysis = Analysis(
                document_id=doc.id,
                status="completed",
                llm_provider="fake",
                llm_model="fake",
                completed_at=datetime.now(timezone.utc),
                run_snapshot={"corpus_version": "abc123"},
            )
            db.add(analysis)
            await db.flush()
            db.add(
                Correction(
                    analysis_id=analysis.id,
                    document_item_id=item.id,
                    category="juridica",
                    severity="alto",
                    situation="s",
                    problem="p",
                    risk="r",
                    original_text="texto original",
                    suggested_text="texto novo",
                    justification="Art. 6º",
                    legal_basis="Art. 6º da Lei 14.133/2021",
                    importance="alta",
                    review_status="aprovada",
                    evidence={
                        "de": "texto original",
                        "para": "texto novo",
                        "corpus_version": "abc123",
                        "grounded": True,
                    },
                )
            )
            await db.commit()
            return await get_audit_pack(analysis.id, db)

    pack = _run(_cenario())
    assert pack.corrections[0].de == "texto original"
    assert pack.corrections[0].para == "texto novo"
    assert pack.corpus_version == "abc123"
