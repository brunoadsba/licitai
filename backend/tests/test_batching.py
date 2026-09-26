"""Testes do batching de itens por chamada LLM (ANALYSIS_BATCH_SIZE).

Cobre: chunking, clamp do settings, atribuição por item_number (drop de
atribuição desconhecida), paridade batch=1, orchestrator em lote (early-exit
por item), revisão em lote e um fluxo engine completo com lote > 1.
"""

import asyncio
import json
import uuid
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models.analysis import Analysis
from app.models.document import Document, DocumentItem
from app.models.retrieval import RetrievalRun  # noqa: F401
from app.services.agents.orchestrator import MultiAgentOrchestrator
from app.services.analyzer.batching import (
    chunk_batches,
    get_batch_size,
    split_corrections_by_item,
)
from app.services.analyzer.engine import run_analysis
from app.services.analyzer.item_analysis import analyze_batch_llm, analyze_item_llm
from app.services.analyzer.review import review_batch_corrections
from app.services.llm.provider import LLMProvider


def _item(number: str, content: str = "Conteudo do item para analise.") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        item_number=number,
        title=f"Item {number}",
        content=content,
        page_number=1,
    )


def _correction(number: str, problem: str = "Problema identificado") -> dict:
    return {
        "category": "juridica",
        "severity": "medio",
        "situation": "Situacao",
        "problem": problem,
        "risk": "Risco",
        "original_text": "trecho original",
        "suggested_text": "texto sugerido",
        "justification": "Justificativa",
        "legal_basis": "Lei 14.133/2021",
        "importance": "media",
        "item_number": number,
    }


class BatchFake(LLMProvider):
    """Fake que responde por marcador de prompt (unitário ou lote)."""

    def __init__(self):
        self.calls = []

    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if "Voce esta revisando" in user_prompt:
            return json.dumps({
                "review": [
                    {"item_number": "1.1", "correction_index": 0,
                     "status": "aprovada", "note": "ok"},
                    {"item_number": "9.9", "correction_index": 0,
                     "status": "aprovada", "note": "fantasma"},
                ]
            })
        if "Revise as correções" in user_prompt:
            return json.dumps({
                "review": [{"correction_index": 0, "status": "aprovada",
                            "note": "ok"}]
            })
        if "AUDITORIA MULTIAGENTE EM LOTE" in user_prompt:
            if "Agente Jurídico" in system_prompt:
                return json.dumps([_correction("1.1")])
            return json.dumps([])
        if "Voce esta auditando" in user_prompt:
            out = []
            for number in ("1.1", "1.2"):
                if f"=== ITEM {number} ===" in user_prompt:
                    out.append(_correction(number))
            out.append(_correction("9.9", problem="Achado fantasma"))
            return json.dumps(out)
        if "Analise o seguinte item" in user_prompt:
            c = _correction("1.1")
            return json.dumps([c])
        return json.dumps({
            "score_overall": 7.5,
            "score_juridical": 8.0,
            "score_technical": 7.0,
            "score_writing": 7.5,
            "score_structural": 7.5,
            "risk_level": "medio",
            "final_opinion": "Parecer final de teste.",
        })


def test_chunk_batches_respeita_tamanho():
    items = [(i, f"ctx{i}") for i in range(5)]
    chunks = chunk_batches(items, 2)
    assert [len(c) for c in chunks] == [2, 2, 1]
    assert chunk_batches(items, 1) == [[i] for i in items]
    assert chunk_batches([], 3) == []


def test_get_batch_size_clampa(monkeypatch):
    monkeypatch.setattr(settings, "analysis_batch_size", 5)
    assert get_batch_size() == 5
    monkeypatch.setattr(settings, "analysis_batch_size", 0)
    assert get_batch_size() == 1
    monkeypatch.setattr(settings, "analysis_batch_size", "invalido")
    assert get_batch_size() == 1


def test_split_descarta_item_number_desconhecido():
    batch = [(_item("1.1"), "ctx"), (_item("1.2"), "ctx")]
    routed = split_corrections_by_item(
        batch, [_correction("1.1"), _correction("1.2"), _correction("9.9")]
    )
    assert len(routed[str(batch[0][0].id)]) == 1
    assert len(routed[str(batch[1][0].id)]) == 1
    assert all(
        c["item_number"] in ("1.1", "1.2")
        for corr in routed.values()
        for c in corr
    )


def test_analyze_batch_llm_roteia_e_descarta_fantasma():
    llm = BatchFake()
    batch = [(_item("1.1"), "ctx1"), (_item("1.2"), "ctx2")]
    out = asyncio.run(analyze_batch_llm(llm, batch))
    assert len(llm.calls) == 1
    assert len(out[str(batch[0][0].id)]) == 1
    assert len(out[str(batch[1][0].id)]) == 1
    assert out[str(batch[0][0].id)][0]["problem"] == "Problema identificado"


def test_batch_de_1equivale_ao_unitario():
    llm = BatchFake()
    item = _item("1.1")
    unitario = asyncio.run(analyze_item_llm(llm, item, "ctx"))
    em_lote = asyncio.run(analyze_batch_llm(llm, [(item, "ctx")]))
    assert len(unitario) == 1
    assert len(em_lote[str(item.id)]) == 1
    for campo in ("category", "severity", "problem", "suggested_text"):
        assert em_lote[str(item.id)][0][campo] == unitario[0][campo]


def test_orchestrator_batch_early_exit_por_item():
    llm = BatchFake()
    orch = MultiAgentOrchestrator()
    orch.agents = orch.agents[:2]
    batch = [(_item("1.1"), "ctx"), (_item("1.2"), "ctx")]
    out = asyncio.run(orch.analyze_batch_multi(llm, batch))
    assert len(out[str(batch[0][0].id)]) == 1
    assert out[str(batch[0][0].id)][0]["agent_origin"] == "juridico"
    assert out[str(batch[1][0].id)] == []
    assert len(llm.calls) == 2


def test_review_batch_endereca_por_item():
    llm = BatchFake()
    batch = [
        (_item("1.1"), "ctx", [_correction("1.1")]),
        (_item("1.2"), "ctx", [_correction("1.2")]),
    ]
    out = asyncio.run(review_batch_corrections(llm, batch))
    assert len(llm.calls) == 1
    assert out[str(batch[0][0].id)] == [
        {"correction_index": 0, "status": "aprovada", "note": "ok",
         "adjusted_suggested_text": None, "adjusted_justification": None}
    ]
    assert out[str(batch[1][0].id)] == []


def test_fluxo_engine_com_lote_2(monkeypatch):
    """run_analysis com ANALYSIS_BATCH_SIZE=2: 2 itens, 1 call de análise."""
    monkeypatch.setattr(settings, "analysis_batch_size", 2)
    llm = BatchFake()

    async def fake_retrieve(db, query, top_k):
        return []

    import app.services.analyzer.engine as engine_mod
    import app.services.llm.factory as factory_mod

    original_provider = factory_mod.get_llm_provider
    factory_mod.get_llm_provider = lambda: llm  # type: ignore[assignment]
    engine_mod.retrieve = fake_retrieve

    async def _run():
        eng = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(eng, expire_on_commit=False)
        async with Session() as session:
            doc = Document(
                filename_original="TR Lote.pdf",
                filename_stored=f"{uuid.uuid4()}.pdf",
                file_type="pdf",
                file_size_bytes=1000,
                document_type="tr",
                status="analyzing",
                classification="publico",
            )
            session.add(doc)
            await session.flush()
            for num in ("1.1", "1.2"):
                session.add(DocumentItem(
                    document_id=doc.id,
                    item_number=num,
                    title=f"Item {num}",
                    content=(
                        "Conteudo do item para analise. A contratacao devera "
                        "observar os requisitos tecnicos e juridicos "
                        "estabelecidos neste termo."
                    ),
                    page_number=1,
                    item_order=int(float(num) * 10),
                    item_type="item",
                ))
            analysis = Analysis(
                document_id=doc.id,
                status="pending",
                llm_provider="fake",
                llm_model="fake-model",
                analysis_mode="single",
            )
            session.add(analysis)
            await session.commit()
            try:
                await run_analysis(session, analysis.id, doc.id)
            finally:
                factory_mod.get_llm_provider = original_provider
            final = await session.get(Analysis, analysis.id)
            return final

    analysis = asyncio.run(_run())
    assert analysis.status == "completed"
    assert analysis.analyzed_items == 2
    analysis_calls = [c for c in llm.calls if "Voce esta auditando" in c[1]]
    assert len(analysis_calls) == 1
