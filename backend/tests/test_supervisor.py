"""Supervisor v1: segunda chance só para altos ainda pendentes.

Mock total (sem LLM, sem banco): FakeLLM aprova o índice 0 do item 9.1;
db é AsyncMock (só conta flush).
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.config import settings
from app.services.analyzer.analysis_phases import _run_supervisor_rereview
from app.services.llm.provider import LLMProvider


def _obj(number="9.1", severity="alto", status="pendente"):
    return SimpleNamespace(
        category="juridica",
        severity=severity,
        situation="s",
        problem="p",
        risk="r",
        original_text="trecho",
        suggested_text="sugestao",
        justification="j",
        legal_basis=None,
        importance="alta" if severity in ("alto", "critico") else "baixa",
        review_status=status,
        review_note=None,
        reviewed_at=None,
    )


def _item(number="9.1"):
    return SimpleNamespace(id=f"id-{number}", item_number=number, title="T",
                           content="conteudo", page_number=1)


class ReFake(LLMProvider):
    def __init__(self, falhar=False):
        self.calls = []
        self.falhar = falhar

    async def health_check(self):
        return True

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-model"

    async def generate(self, system_prompt, user_prompt):
        self.calls.append(user_prompt)
        if self.falhar:
            raise RuntimeError("quota")
        return json.dumps({
            "review": [{"item_number": "9.1", "correction_index": 0,
                        "status": "aprovada", "note": "ok"}]
        })


def _db():
    return SimpleNamespace(flush=AsyncMock())


def test_vira_alto_pendente_em_aprovada(monkeypatch):
    monkeypatch.setattr(settings, "supervisor_rereview_high", True)
    monkeypatch.setattr(settings, "analysis_batch_size", 1)
    llm, db = ReFake(), _db()
    alto, baixo = _obj("9.1", "alto"), _obj("9.2", "baixo")
    pending = [(_item("9.1"), "ctx", [alto]), (_item("9.2"), "ctx", [baixo])]
    flipped = asyncio.run(_run_supervisor_rereview(db, llm, pending))
    assert alto.review_status == "aprovada"
    assert baixo.review_status == "pendente"
    assert len(flipped) == 1
    assert len(llm.calls) == 1
    db.flush.assert_awaited()


def test_sem_alto_nao_chama_llm(monkeypatch):
    monkeypatch.setattr(settings, "supervisor_rereview_high", True)
    llm, db = ReFake(), _db()
    baixo = _obj("9.2", "baixo")
    out = asyncio.run(_run_supervisor_rereview(
        db, llm, [(_item("9.2"), "ctx", [baixo])]))
    assert out == []
    assert llm.calls == []


def test_falha_mantem_pendente(monkeypatch):
    monkeypatch.setattr(settings, "supervisor_rereview_high", True)
    monkeypatch.setattr(settings, "analysis_batch_size", 1)
    llm, db = ReFake(falhar=True), _db()
    alto = _obj("9.1", "alto")
    out = asyncio.run(_run_supervisor_rereview(
        db, llm, [(_item("9.1"), "ctx", [alto])]))
    assert out == []
    assert alto.review_status == "pendente"


def test_desligado_pula(monkeypatch):
    monkeypatch.setattr(settings, "supervisor_rereview_high", False)
    llm, db = ReFake(), _db()
    alto = _obj("9.1", "alto")
    out = asyncio.run(_run_supervisor_rereview(
        db, llm, [(_item("9.1"), "ctx", [alto])]))
    assert out == []
    assert llm.calls == []
    assert alto.review_status == "pendente"
