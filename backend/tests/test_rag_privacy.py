"""Trava de privacidade do rerank LLM do RAG (R3) + selo claim_support.

Garante: documento sigiloso nunca vai a provedor cloud no `llm_rerank`
(Ollama local sempre passa; modo != llm nunca injeta LLM).
E: `Correction.claim_support` serializa {"supported","total"} ou None.
"""

import uuid

from app.config import settings
from app.models.analysis import Correction
from app.schemas.analysis import CorrectionResponse
from app.services.privacy import llm_rerank_allowed_for_document


def _correction(**overrides):
    base = dict(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        document_item_id=uuid.uuid4(),
        category="juridica",
        severity="alto",
        situation="s",
        problem="p",
        risk="r",
        original_text="o",
        suggested_text="s",
        justification="j",
        importance="alta",
        review_status="pendente",
    )
    base.update(overrides)
    return Correction(**base)


def test_rerank_llm_bloqueado_com_modo_off_ou_heuristic():
    assert llm_rerank_allowed_for_document("publico", rerank_mode="off") is False
    assert llm_rerank_allowed_for_document("publico", rerank_mode="heuristic") is False
    assert llm_rerank_allowed_for_document("sigiloso", rerank_mode="off") is False


def test_rerank_llm_bloqueia_sigiloso_em_cloud():
    assert (
        llm_rerank_allowed_for_document(
            "sigiloso", rerank_mode="llm", provider="groq"
        )
        is False
    )
    assert (
        llm_rerank_allowed_for_document(
            "Sigiloso", rerank_mode="llm", provider="gemini"
        )
        is False
    )


def test_rerank_llm_permite_sigiloso_local_e_publico_cloud():
    assert (
        llm_rerank_allowed_for_document(
            "sigiloso", rerank_mode="llm", provider="ollama"
        )
        is True
    )
    assert (
        llm_rerank_allowed_for_document(
            "publico", rerank_mode="llm", provider="groq"
        )
        is True
    )
    assert (
        llm_rerank_allowed_for_document(None, rerank_mode="llm", provider="groq")
        is True
    )


def test_rerank_llm_usa_modo_do_settings_por_padrao(monkeypatch):
    monkeypatch.setattr(settings, "rag_rerank_mode", "llm")
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert llm_rerank_allowed_for_document("publico") is True
    assert llm_rerank_allowed_for_document("sigiloso") is False
    monkeypatch.setattr(settings, "rag_rerank_mode", "heuristic")
    assert llm_rerank_allowed_for_document("publico") is False


def test_claim_support_serializa_quando_valido():
    c = _correction(evidence={"claim_support": {"supported": 2, "total": 3}})
    assert c.claim_support == {"supported": 2, "total": 3}
    resp = CorrectionResponse.model_validate(c)
    assert resp.claim_support is not None
    assert resp.claim_support.supported == 2
    assert resp.claim_support.total == 3


def test_claim_support_none_quando_ausente_ou_invalido():
    assert _correction(evidence=None).claim_support is None
    assert _correction(evidence={}).claim_support is None
    assert (
        _correction(evidence={"claim_support": {"supported": 9, "total": 3}}).claim_support
        is None
    )
    assert (
        _correction(evidence={"claim_support": "2/3"}).claim_support is None
    )
    resp = CorrectionResponse.model_validate(_correction(evidence=None))
    assert resp.claim_support is None
