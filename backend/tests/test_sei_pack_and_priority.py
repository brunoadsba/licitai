"""Testes de severity_min, pacote SEI e HTML corrigido."""

from __future__ import annotations

import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.analysis import _filter_corrections
from app.database import Base, get_db
from app.main import app
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.services.analyzer.corrected_document import (
    apply_sei_corrections_to_text,
    build_corrected_docx,
    build_corrected_html,
    build_sei_pack_text,
)


def _run(coro):
    return asyncio.run(coro)


async def _montar_cenario_multi() -> tuple[async_sessionmaker, dict]:
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
            filename_original="TR-pack.pdf",
            filename_stored="tr-pack.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="completed",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        item_a = DocumentItem(
            document_id=doc.id,
            item_number="1.1",
            title="Objeto",
            content="Texto A com trecho DE.",
            item_order=1,
        )
        item_b = DocumentItem(
            document_id=doc.id,
            item_number="2.0",
            title="Prazo",
            content="Texto B intacto.",
            item_order=2,
        )
        session.add_all([item_a, item_b])
        await session.commit()
        await session.refresh(item_a)
        await session.refresh(item_b)

        analysis = Analysis(
            document_id=doc.id,
            status="completed",
            llm_provider="groq",
            llm_model="test",
            analysis_mode="multi_agent",
            total_items=2,
            analyzed_items=2,
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)

        c_aprovada = Correction(
            analysis_id=analysis.id,
            document_item_id=item_a.id,
            category="juridica",
            severity="critico",
            situation="S",
            problem="P",
            risk="R",
            original_text="trecho DE",
            suggested_text="trecho PARA",
            justification="Justificativa A",
            legal_basis="Lei 14.133",
            importance="alta",
            review_status="aprovada",
        )
        c_pendente = Correction(
            analysis_id=analysis.id,
            document_item_id=item_b.id,
            category="tecnica",
            severity="alto",
            situation="S",
            problem="P",
            risk="R",
            original_text="Texto B",
            suggested_text="Texto B novo",
            justification="Justificativa B",
            importance="alta",
            review_status="pendente",
        )
        c_baixo = Correction(
            analysis_id=analysis.id,
            document_item_id=item_b.id,
            category="redacao",
            severity="baixo",
            situation="S",
            problem="P",
            risk="R",
            original_text="x",
            suggested_text="y",
            justification="J",
            importance="baixa",
            review_status="aprovada",
        )
        session.add_all([c_aprovada, c_pendente, c_baixo])
        await session.commit()

        ids = {
            "analysis_id": analysis.id,
            "document_id": doc.id,
        }
    return Session, ids


async def _get(Session, path: str):
    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get(path)
            return {"status_code": resp.status_code, "json": resp.json()}
    finally:
        app.dependency_overrides.clear()


def test_filter_severity_min_alto():
    class C:
        def __init__(self, severity: str, status: str = "pendente"):
            self.severity = severity
            self.review_status = status

    items = [C("baixo"), C("alto"), C("critico"), C("medio")]
    filtered = _filter_corrections(items, severity_min="alto")
    assert {c.severity for c in filtered} == {"alto", "critico"}


def test_filter_severity_min_com_review_status():
    class C:
        def __init__(self, severity: str, status: str):
            self.severity = severity
            self.review_status = status

    items = [
        C("critico", "pendente"),
        C("alto", "aprovada"),
        C("medio", "pendente"),
    ]
    filtered = _filter_corrections(
        items, review_statuses={"pendente"}, severity_min="alto"
    )
    assert len(filtered) == 1
    assert filtered[0].severity == "critico"


def test_sei_pack_vazio_sem_aprovadas():
    Session, ids = _run(_montar_cenario_multi())

    async def zero_aprovadas():
        async with Session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Correction).where(Correction.analysis_id == ids["analysis_id"])
            )
            for c in result.scalars().all():
                c.review_status = "pendente"
            await session.commit()

    _run(zero_aprovadas())
    result = _run(_get(Session, f"/api/v1/analysis/{ids['analysis_id']}/sei-pack"))
    assert result["status_code"] == 200
    assert result["json"]["total"] == 0
    assert "Nenhuma correção" in result["json"]["text"]


def test_sei_pack_ordenado_e_so_aprovadas():
    Session, ids = _run(_montar_cenario_multi())
    result = _run(_get(Session, f"/api/v1/analysis/{ids['analysis_id']}/sei-pack"))
    assert result["status_code"] == 200
    data = result["json"]
    assert data["total"] == 2  # critico aprovada + baixo aprovada
    numbers = [e["item_number"] for e in data["entries"]]
    assert numbers == ["1.1", "2.0"]
    assert all(e["suggested_text"] for e in data["entries"])


def test_corrected_html_404_sem_aprovadas():
    Session, ids = _run(_montar_cenario_multi())

    async def zero():
        async with Session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Correction).where(Correction.analysis_id == ids["analysis_id"])
            )
            for c in result.scalars().all():
                c.review_status = "rejeitada"
            await session.commit()

    _run(zero())
    result = _run(
        _get(Session, f"/api/v1/analysis/{ids['analysis_id']}/corrected-html")
    )
    assert result["status_code"] == 404


def test_corrected_html_409_analise_incompleta():
    Session, ids = _run(_montar_cenario_multi())

    async def mark_running():
        async with Session() as session:
            analysis = await session.get(Analysis, ids["analysis_id"])
            analysis.status = "running"
            await session.commit()

    _run(mark_running())
    result = _run(
        _get(Session, f"/api/v1/analysis/{ids['analysis_id']}/corrected-html")
    )
    assert result["status_code"] == 409


def test_corrected_html_aplica_replace():
    Session, ids = _run(_montar_cenario_multi())
    result = _run(
        _get(Session, f"/api/v1/analysis/{ids['analysis_id']}/corrected-html")
    )
    assert result["status_code"] == 200
    html = result["json"]["html"]
    assert "trecho PARA" in html
    assert "trecho DE" not in html
    assert result["json"]["applied_corrections"] >= 1


def test_build_helpers_unit():
    class FakeCorr:
        id = uuid.uuid4()
        review_status = "aprovada"
        original_text = "DE"
        suggested_text = "PARA"

    text, applied, skipped = apply_sei_corrections_to_text("x DE y", [FakeCorr()])
    assert text == "x PARA y"
    assert len(applied) == 1
    assert skipped == []

    # whitespace / acentos
    class FakeCorr2:
        id = uuid.uuid4()
        review_status = "aprovada"
        original_text = "definição  do objeto"
        suggested_text = "definição clara do objeto"

    text2, applied2, skipped2 = apply_sei_corrections_to_text(
        "A definição   do objeto consta aqui.", [FakeCorr2()]
    )
    assert "definição clara do objeto" in text2
    assert len(applied2) == 1

    class FakeMiss:
        id = uuid.uuid4()
        review_status = "aprovada"
        original_text = "trecho inexistente XYZ"
        suggested_text = "novo"

    _, _, skipped3 = apply_sei_corrections_to_text("texto normal", [FakeMiss()])
    assert skipped3 and skipped3[0]["reason"] == "not_found"

    html, applied_h, skipped_h = build_corrected_html(
        filename="TR.pdf",
        items=[
            type(
                "I",
                (),
                {
                    "id": uuid.uuid4(),
                    "item_order": 0,
                    "item_number": "1",
                    "title": "T",
                    "content": "DE",
                },
            )()
        ],
        corrections_by_item={},
    )
    assert "<h1>" in html
    assert applied_h == []
    text = build_sei_pack_text(document_name="TR", entries=[])
    assert "Nenhuma correção" in text


def test_build_corrected_docx_bytes():
    item_id = uuid.uuid4()

    class FakeCorr:
        id = uuid.uuid4()
        review_status = "aprovada"
        original_text = "antigo"
        suggested_text = "novo"

    payload, applied, skipped = build_corrected_docx(
        filename="TR-teste.pdf",
        items=[
            type(
                "I",
                (),
                {
                    "id": item_id,
                    "item_order": 0,
                    "item_number": "1.1",
                    "title": "Objeto",
                    "content": "Texto antigo aqui.",
                },
            )()
        ],
        corrections_by_item={item_id: [FakeCorr()]},
    )
    assert payload[:2] == b"PK"  # zip/docx
    assert len(applied) == 1
    assert skipped == []
