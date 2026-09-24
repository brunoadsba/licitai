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
from app.models.retrieval import RetrievalRun  # noqa: F401
from app.services.analyzer.engine import run_analysis
from app.services.llm.provider import LLMProvider

logging.basicConfig(level=logging.WARNING)


class FakeLLM(LLMProvider):
    """Provider fake que responde conforme o prompt (item/revisão/pontuação)."""

    def __init__(self, falhar_pontuacao: bool = False, pontuacao_invalida: bool = False):
        self._falhar_pontuacao = falhar_pontuacao
        self._pontuacao_invalida = pontuacao_invalida

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
                "original_text": "Conteúdo do item para análise.",
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
        if self._pontuacao_invalida:
            return json.dumps({
                "score_overall": "12",
                "score_juridical": True,
                "score_technical": 7.0,
                "score_writing": 7.5,
                "score_structural": 7.5,
                "risk_level": "medio",
                "final_opinion": "Parecer final de teste.",
            })
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
    pontuacao_invalida: bool = False,
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
    llm = FakeLLM(
        falhar_pontuacao=falhar_pontuacao,
        pontuacao_invalida=pontuacao_invalida,
    )

    async def fake_retrieve(db, query, top_k):
        return []

    import app.services.analyzer.engine as engine_mod
    import app.services.llm.factory as factory_mod

    original_provider = factory_mod.get_llm_provider
    factory_mod.get_llm_provider = lambda: llm  # type: ignore[assignment]
    engine_mod.retrieve = fake_retrieve

    async with Session() as session:
        doc = Document(
            filename_original="TR Teste.pdf",
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
                    "Conteúdo do item para análise. A contratação deverá observar "
                    "os requisitos técnicos e jurídicos estabelecidos neste termo."
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

        doc_id = uuid.uuid4() if documento_inexistente else doc.id
        try:
            await run_analysis(session, analysis.id, doc_id)
        finally:
            factory_mod.get_llm_provider = original_provider

        status_analysis = await session.get(Analysis, analysis.id)
        status_doc = await session.get(Document, doc.id)
        n_corrections = (
            await session.execute(select(func.count()).select_from(Correction))
        ).scalar_one()
        return status_analysis, status_doc, n_corrections


def _fluxo(**kwargs):
    return asyncio.run(_montar_e_analisar(**kwargs))


def test_sanitize_scores_clampa_e_valida():
    from app.services.analyzer.scoring import sanitize_scores

    scores = sanitize_scores({
        "score_overall": 11,
        "score_juridical": -1.4,
        "score_technical": 7.0,
        "score_writing": 7.55,
        "score_structural": 8,
        "risk_level": "ALTO ",
        "final_opinion": "Ok.",
    })

    assert scores["score_overall"] == 10.0
    assert scores["score_juridical"] == 0.0
    assert scores["score_writing"] == 7.5
    assert scores["score_structural"] == 8.0
    assert scores["risk_level"] == "alto"


def test_sanitize_scores_rejeita_nao_numericas():
    import pytest

    from app.services.analyzer.scoring import sanitize_scores

    with pytest.raises(ValueError):
        sanitize_scores({
            "score_overall": "12",
            "score_juridical": True,
            "score_technical": 7.0,
            "score_writing": 7.5,
            "score_structural": 7.5,
        })

    with pytest.raises(ValueError):
        sanitize_scores({"score_overall": None})


def test_run_analysis_completa_fluxo_single_agent():
    """Fluxo completo: item analisado, revisado, pontuado e análise concluída."""
    analysis, doc, n_corrections = _fluxo()

    assert analysis.status == "completed"
    assert analysis.total_items == 2
    assert analysis.analyzed_items == 2
    # Scoring determinístico primário (2 correções juridica/medio → 9.5)
    assert float(analysis.score_overall) == 9.5
    assert analysis.risk_level == "baixo"
    # Opinião LLM secundária + rodapé de origens (Fase 1)
    assert analysis.final_opinion.startswith("Parecer final de teste.")
    assert "Fontes do parecer" in analysis.final_opinion
    snapshot = analysis.run_snapshot or {}
    assert snapshot.get("origin_correction_ids")
    assert snapshot.get("retrieval_run_ids") is not None
    assert analysis.started_at is not None
    assert analysis.completed_at is not None
    assert doc.status == "completed"
    assert n_corrections == 2


def test_run_analysis_usa_fallback_quando_llm_falha_pontuacao():
    """Falha na sumarização final mantém opinião determinística."""
    analysis, doc, n_corrections = _fluxo(falhar_pontuacao=True)

    assert analysis.status == "completed"
    assert analysis.score_overall is not None
    assert analysis.risk_level in {"baixo", "medio", "alto", "critico"}
    assert "Pontuação consolidada" in analysis.final_opinion
    assert n_corrections == 2


def test_run_analysis_usa_fallback_quando_llm_devolve_notas_invalidas():
    """Notas inválidas do LLM: scores determinísticos; opinião LLM ignorada."""
    analysis, doc, n_corrections = _fluxo(pontuacao_invalida=True)

    assert analysis.status == "completed"
    assert isinstance(float(analysis.score_overall), float)
    assert 0.0 <= float(analysis.score_overall) <= 10.0
    assert "Pontuação consolidada" in analysis.final_opinion
    assert n_corrections == 2


def test_run_analysis_erro_quando_documento_inexistente():
    """Documento não encontrado marca a análise como erro sem quebrar."""
    analysis, _, n_corrections = _fluxo(documento_inexistente=True)

    assert analysis.status == "error"
    assert "Documento não encontrado" in analysis.error_message
    assert n_corrections == 0

def test_select_items_ignora_titulos_e_prioriza_clausulas():
    """Orçamento deve cair só em cláusulas substantivas, não em títulos."""
    from app.services.analyzer.item_selection import select_items_for_analysis

    heading = DocumentItem(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        item_number="01",
        title="OBJETO DA CONTRATAÇÃO",
        content="01 – OBJETO DA CONTRATAÇÃO",
        item_order=0,
        item_type="section",
    )
    clause_obj = DocumentItem(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        item_number="1.1",
        title="Objeto",
        content=(
            "1.1. A presente contratação tem por objeto a prestação de serviços "
            "de telefonia fixa corporativa com PABX em nuvem."
        ),
        item_order=1,
        item_type="item",
    )
    clause_late = DocumentItem(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        item_number="9.1",
        title="Matriz",
        content=(
            "9.1. A matriz de riscos identifica eventos de atraso na implantação "
            "e define responsabilidades entre as partes contratantes."
        ),
        item_order=2,
        item_type="item",
    )

    work, skipped, truncated = select_items_for_analysis(
        [heading, clause_obj, clause_late],
        max_items=1,
    )
    assert len(skipped) == 1
    assert skipped[0].item_number == "01"
    assert truncated is True
    assert len(work) == 1
    assert work[0].item_number == "1.1"  # prioridade seção 1 sobre 9


def test_select_items_sem_limite_mantem_todos_substantivos():
    from app.services.analyzer.item_selection import select_items_for_analysis

    items = [
        DocumentItem(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            item_number="2.1",
            title="Solução",
            content=(
                "2.1. A solução objeto da contratação consiste na prestação "
                "integrada de serviços de telefonia fixa corporativa."
            ),
            item_order=0,
            item_type="item",
        ),
        DocumentItem(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            item_number="2",
            title="DESCRIÇÃO",
            content="2. DESCRIÇÃO DA SOLUÇÃO DE TIC",
            item_order=1,
            item_type="section",
        ),
    ]
    work, skipped, truncated = select_items_for_analysis(items, max_items=None)
    assert truncated is False
    assert len(work) == 1
    assert work[0].item_number == "2.1"
    assert len(skipped) == 1
