"""
Testes de regressão do motor de análise (app.services.analyzer.engine).

Cobre o fluxo completo de `run_analysis` em modo single-agent com provider
fake: item analisado → revisão cruzada → pontuação → status final, além do
fallback determinístico de pontuação quando o LLM falha na sumarização.
"""

import asyncio
import json
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.analysis import Analysis, Correction
from app.models.document import Document, DocumentItem
from app.services.analyzer.engine import run_analysis
from app.services.llm.provider import LLMProvider

logging.basicConfig(level=logging.WARNING)


class FakeLLM(LLMProvider):
    """Provider fake que responde conforme o prompt (item/revisão/pontuação)."""

    def __init__(self, falhar_pontuacao: bool = False):
        self._falhar_pontuacao = falhar_pontuacao

    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "Analise o seguinte item" in user_prompt:
            return json.dumps([{
                "category": "juridica",
                "severity": "medio",
                "situation": "Situação do item",
                "problem": "Problema identificado",
                "risk": "Risco de descumprimento",
                "original_text": "Texto original",
                "suggested_text": "Texto sugerido",
                "justification": "Fundamentação",
                "legal_basis": "Lei 14.133/2021",
                "importance": "media",
            }])
        if "Revise as correções" in user_prompt:
            return json.dumps({
                "review": [{"correction_index": 0, "status": "aprovada", "note": "ok"}]
            })
        if self._falhar_pontuacao:
            return "resposta inválida sem json"
        return json.dumps({
            "score_overall": 7.5,
            "score_juridical": 8.0,
            "score_technical": 7.0,
            "score_writing": 7.5,
            "score_structural": 7.5,
            "risk_level": "medio",
            "final_opinion": "Parecer final de teste.",
        })


async def _montar_e_analisar(
    falhar_pontuacao: bool = False,
    documento_inexistente: bool = False,
) -> tuple[Analysis, Document | None, int]:
    """Cria banco em memória, roda run_analysis com mocks e devolve estado final."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    llm = FakeLLM(falhar_pontuacao=falhar_pontuacao)

    async def fake_retrieve(db, query, top_k):
        return []

    import app.services.analyzer.engine as engine_mod

    engine_mod.get_llm_provider = lambda: llm  # chamada síncrona no engine
    engine_mod.retrieve = fake_retrieve

    async with Session() as session:
        doc = Document(
            filename_original="TR Teste.pdf",
            filename_stored=f"{uuid.uuid4()}.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="analyzing",
        )
        session.add(doc)
        await session.flush()

        for num in ("1.1", "1.2"):
            session.add(DocumentItem(
                document_id=doc.id,
                item_number=num,
                title=f"Item {num}",
                content="Conteúdo do item para análise.",
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

        doc_id = uuid.uuid4() if documento_inexistente else doc.id
        await run_analysis(session, analysis.id, doc_id)

        status_analysis = await session.get(Analysis, analysis.id)
        status_doc = await session.get(Document, doc.id)
        n_corrections = (
            await session.execute(select(func.count()).select_from(Correction))
        ).scalar_one()
        return status_analysis, status_doc, n_corrections


def _fluxo(**kwargs):
    return asyncio.run(_montar_e_analisar(**kwargs))


def test_run_analysis_completa_fluxo_single_agent():
    """Fluxo completo: item analisado, revisado, pontuado e análise concluída."""
    analysis, doc, n_corrections = _fluxo()

    assert analysis.status == "completed"
    assert analysis.total_items == 2
    assert analysis.analyzed_items == 2
    assert float(analysis.score_overall) == 7.5
    assert analysis.risk_level == "medio"
    assert analysis.final_opinion == "Parecer final de teste."
    assert analysis.started_at is not None
    assert analysis.completed_at is not None
    assert doc.status == "completed"
    assert n_corrections == 2


def test_run_analysis_usa_fallback_quando_llm_falha_pontuacao():
    """Falha na sumarização final cai no cálculo determinístico de fallback."""
    analysis, doc, n_corrections = _fluxo(falhar_pontuacao=True)

    assert analysis.status == "completed"
    assert analysis.score_overall is not None
    assert analysis.risk_level in {"baixo", "medio", "alto", "critico"}
    assert "Pontuação consolidada" in analysis.final_opinion
    assert n_corrections == 2


def test_run_analysis_erro_quando_documento_inexistente():
    """Documento não encontrado marca a análise como erro sem quebrar."""
    analysis, _, n_corrections = _fluxo(documento_inexistente=True)

    assert analysis.status == "error"
    assert "Documento não encontrado" in analysis.error_message
    assert n_corrections == 0