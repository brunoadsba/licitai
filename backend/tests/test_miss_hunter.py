"""Miss-hunter v1: 2ª passada só nos itens "ok" (zero correções).

Mock total (sem LLM real, sem banco): HunterFake devolve um achado com
evidência local para o item-alvo; persist/cross-review/supervisor são
substituídos por fakes no teste de orquestração.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.config import settings
from app.services.analyzer import miss_hunter
from app.services.analyzer.miss_hunter import (
    _run_miss_hunter,
    select_hunter_targets,
)
from app.services.llm.provider import LLMProvider


def _item(number="4.3"):
    return SimpleNamespace(id=f"id-{number}", item_number=number, title="T",
                           content="conteudo do item com prazo de 30 dias",
                           page_number=1)


class HunterFake(LLMProvider):
    def __init__(self, finding=True):
        self.systems = []
        self.users = []
        self.finding = finding

    async def health_check(self):
        return True

    @property
    def provider_name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-model"

    async def generate(self, system_prompt, user_prompt):
        self.systems.append(system_prompt)
        self.users.append(user_prompt)
        if not self.finding:
            return json.dumps([])
        return json.dumps([{
            "item_number": "4.3",
            "category": "juridica",
            "severity": "alto",
            "situation": "s",
            "problem": "prazo de 30 dias sem regra de prorrogação",
            "risk": "r",
            "original_text": "prazo de 30 dias",
            "suggested_text": "prazo de 30 dias, prorrogável",
            "justification": "j",
            "legal_basis": None,
            "importance": "alta",
        }])


def _pending(number="4.3", objs="empty"):
    return (_item(number), "ctx", [] if objs == "empty" else [object()])


def test_seleciona_so_ok_e_respeita_teto():
    pend = [_pending("4.3"), _pending("4.4", "full"), _pending("4.5")]
    assert [i.item_number for i, _ in select_hunter_targets(pend, 10)] == ["4.3", "4.5"]
    assert len(select_hunter_targets(pend, 1)) == 1
    assert select_hunter_targets(pend, 0) == []


def test_desligado_nao_chama_llm(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", False)
    llm = HunterFake()
    out = asyncio.run(_run_miss_hunter(
        SimpleNamespace(), SimpleNamespace(), SimpleNamespace(), "doc",
        llm, [_pending()], {}, set()))
    assert out == []
    assert llm.users == []


def test_sem_alvo_nao_chama_llm(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", True)
    monkeypatch.setattr(settings, "miss_hunter_max_items", 10)
    llm = HunterFake()
    out = asyncio.run(_run_miss_hunter(
        SimpleNamespace(), SimpleNamespace(), SimpleNamespace(), "doc",
        llm, [_pending("4.4", "full")], {}, set()))
    assert out == []
    assert llm.users == []


def test_orcamento_estourado_pula(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", True)
    llm = HunterFake()
    out = asyncio.run(_run_miss_hunter(
        SimpleNamespace(), SimpleNamespace(), SimpleNamespace(), "doc",
        llm, [_pending()], {}, set(), budget_truncated=True))
    assert out == []
    assert llm.users == []


def test_lente_hunter_no_prompt(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", True)
    monkeypatch.setattr(settings, "miss_hunter_max_items", 10)
    monkeypatch.setattr(settings, "analysis_batch_size", 1)

    async def fake_persist(db, analysis, document, doc_id, targets, results,
                           valid_refs, total, truncated, retrieval):
        assert len(targets) == 1
        assert len(results) == 1 and len(results[0]) == 1
        return {"pending_reviews": [(targets[0][0], "ctx", ["c1"])]}

    async def fake_review(db, llm, pendings):
        return [{"kept": True}]

    async def fake_super(db, llm, pendings):
        return []

    monkeypatch.setattr(miss_hunter, "persist_item_outcomes", fake_persist)
    monkeypatch.setattr(miss_hunter, "_run_cross_review", fake_review)
    monkeypatch.setattr(miss_hunter, "_run_supervisor_rereview", fake_super)

    analysis = SimpleNamespace(run_snapshot={}, analyzed_items=5)
    db = SimpleNamespace(flush=AsyncMock())
    llm = HunterFake()
    out = asyncio.run(_run_miss_hunter(
        db, analysis, SimpleNamespace(items=[]), "doc",
        llm, [_pending()], {"id-4.3": {}}, set()))
    assert out == [{"kept": True}]
    assert "MISS-HUNTER" in llm.systems[0]
    assert "SEGUNDA PASSADA" in llm.users[0]
    assert analysis.analyzed_items == 5
    assert analysis.run_snapshot["analyzed_item_ids"] == []
    db.flush.assert_awaited()


def test_hunter_vazio_honesto(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", True)
    monkeypatch.setattr(settings, "miss_hunter_max_items", 10)
    monkeypatch.setattr(settings, "analysis_batch_size", 1)
    seen = {}

    async def fake_persist(db, analysis, document, doc_id, targets, results,
                           valid_refs, total, truncated, retrieval):
        seen["results"] = results
        return {"pending_reviews": []}

    async def fake_review(db, llm, pendings):
        return []

    async def fake_super(db, llm, pendings):
        return []

    monkeypatch.setattr(miss_hunter, "persist_item_outcomes", fake_persist)
    monkeypatch.setattr(miss_hunter, "_run_cross_review", fake_review)
    monkeypatch.setattr(miss_hunter, "_run_supervisor_rereview", fake_super)

    llm = HunterFake(finding=False)
    out = asyncio.run(_run_miss_hunter(
        SimpleNamespace(flush=AsyncMock()),
        SimpleNamespace(run_snapshot={}, analyzed_items=5),
        SimpleNamespace(items=[]), "doc",
        llm, [_pending()], {}, set()))
    assert out == []
    assert seen["results"] == [[]]


def test_snapshot_mesclado_sem_duplicar(monkeypatch):
    monkeypatch.setattr(settings, "miss_hunter_enabled", True)
    monkeypatch.setattr(settings, "miss_hunter_max_items", 10)
    monkeypatch.setattr(settings, "analysis_batch_size", 1)

    async def fake_persist(db, analysis, document, doc_id, targets, results,
                           valid_refs, total, truncated, retrieval):
        analysis.run_snapshot = {
            "analyzed_item_ids": ["id-4.3", "id-9.9"],
            "failed_item_ids": [],
            "origin_correction_ids": ["new-1"],
        }
        analysis.analyzed_items = 1
        return {"pending_reviews": []}

    async def fake_review(db, llm, pendings):
        return []

    async def fake_super(db, llm, pendings):
        return []

    monkeypatch.setattr(miss_hunter, "persist_item_outcomes", fake_persist)
    monkeypatch.setattr(miss_hunter, "_run_cross_review", fake_review)
    monkeypatch.setattr(miss_hunter, "_run_supervisor_rereview", fake_super)

    analysis = SimpleNamespace(
        run_snapshot={
            "analyzed_item_ids": ["id-4.1", "id-4.3"],
            "failed_item_ids": ["id-4.0"],
            "origin_correction_ids": ["old-1"],
        },
        analyzed_items=2,
    )
    out = asyncio.run(_run_miss_hunter(
        SimpleNamespace(flush=AsyncMock()), analysis,
        SimpleNamespace(items=[]), "doc",
        HunterFake(), [_pending()], {}, set()))
    assert out == []
    assert analysis.run_snapshot["analyzed_item_ids"] == ["id-4.1", "id-4.3", "id-9.9"]
    assert analysis.run_snapshot["failed_item_ids"] == ["id-4.0"]
    assert analysis.run_snapshot["origin_correction_ids"] == ["old-1", "new-1"]
    assert analysis.analyzed_items == 2
