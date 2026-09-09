"""Testes do PATCH /analysis/corrections/{id} — revisão humana SEI."""

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.analysis import SEI_APPLICABLE_STATUSES, _filter_corrections
from app.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem


async def _montar_cenario() -> tuple[async_sessionmaker, dict]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        doc = Document(
            filename_original="TR-review.pdf",
            filename_stored="tr-review.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="completed",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        item = DocumentItem(
            document_id=doc.id,
            item_number="1",
            title="Objeto",
            content="Texto original do item.",
            item_order=0,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)

        analysis = Analysis(
            document_id=doc.id,
            status="completed",
            llm_provider="groq",
            llm_model="test",
            analysis_mode="multi_agent",
            total_items=1,
            analyzed_items=1,
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

        correction = Correction(
            analysis_id=analysis.id,
            document_item_id=item.id,
            category="juridica",
            severity="alto",
            situation="Situação",
            problem="Problema",
            risk="Risco",
            original_text="Texto original",
            suggested_text="Texto sugerido",
            justification="Justificativa",
            importance="alta",
            review_status="pendente",
        )
        session.add(correction)
        await session.commit()
        await session.refresh(correction)

        ids = {
            "correction_id": correction.id,
            "analysis_id": analysis.id,
        }
    return Session, ids


def _run(coroutine):
    return asyncio.run(coroutine)


async def _patch_review(Session, correction_id: uuid.UUID, body: dict):
    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.patch(
                f"/api/v1/analysis/corrections/{correction_id}",
                json=body,
            )
            return {"status_code": resp.status_code, "json": resp.json()}
    finally:
        app.dependency_overrides.clear()


def test_patch_aprovar_libera_sei():
    Session, ids = _run(_montar_cenario())
    result = _run(
        _patch_review(
            Session,
            ids["correction_id"],
            {"review_status": "aprovada", "review_note": "OK"},
        )
    )
    assert result["status_code"] == 200
    data = result["json"]
    assert data["review_status"] == "aprovada"
    assert data["review_note"] == "OK"
    assert data["reviewed_at"] is not None
    assert data["review_status"] in SEI_APPLICABLE_STATUSES


def test_patch_rejeitar_nao_libera_sei():
    Session, ids = _run(_montar_cenario())
    result = _run(
        _patch_review(Session, ids["correction_id"], {"review_status": "rejeitada"})
    )
    assert result["status_code"] == 200
    assert result["json"]["review_status"] == "rejeitada"
    assert result["json"]["review_status"] not in SEI_APPLICABLE_STATUSES


def test_patch_ajustada_atualiza_texto():
    Session, ids = _run(_montar_cenario())
    result = _run(
        _patch_review(
            Session,
            ids["correction_id"],
            {
                "review_status": "ajustada",
                "suggested_text": "Texto ajustado pelo SEI",
                "review_note": "Ajuste editorial",
            },
        )
    )
    assert result["status_code"] == 200
    data = result["json"]
    assert data["review_status"] == "ajustada"
    assert data["suggested_text"] == "Texto ajustado pelo SEI"
    assert data["review_status"] in SEI_APPLICABLE_STATUSES


def test_patch_ajustada_sem_campos_falha():
    Session, ids = _run(_montar_cenario())
    result = _run(
        _patch_review(Session, ids["correction_id"], {"review_status": "ajustada"})
    )
    assert result["status_code"] == 422


def test_patch_pendente_limpa_reviewed_at():
    Session, ids = _run(_montar_cenario())
    _run(
        _patch_review(Session, ids["correction_id"], {"review_status": "aprovada"})
    )
    result = _run(
        _patch_review(Session, ids["correction_id"], {"review_status": "pendente"})
    )
    assert result["status_code"] == 200
    assert result["json"]["review_status"] == "pendente"
    assert result["json"]["reviewed_at"] is None


def test_patch_404():
    Session, _ids = _run(_montar_cenario())
    result = _run(
        _patch_review(
            Session,
            uuid.uuid4(),
            {"review_status": "aprovada"},
        )
    )
    assert result["status_code"] == 404


def test_filter_sei_apos_aprovacao():
    class C:
        def __init__(self, status: str):
            self.review_status = status

    filtered = _filter_corrections(
        [C("aprovada"), C("rejeitada")], for_sei=True
    )
    assert len(filtered) == 1
    assert filtered[0].review_status == "aprovada"
