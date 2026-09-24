"""Fase 7: custo, cache de embedding e métricas p50/p95."""

from app.services.cost import estimate_tokens, record_operation_cost
from app.services.privacy import is_restricted
from app.services.rag.embed_store import load_vector, store_vector
from app.utils.metrics import MetricsRegistry


def test_custo_registrado_e_limitado():
    rec = record_operation_cost("chat", 2000)
    assert rec.tokens == 2000
    assert rec.usd > 0
    assert estimate_tokens("abcd") == 1


def test_embed_store_nao_cruza_classificacao(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.rag.embed_store.UPLOAD_DIR", tmp_path)
    store_vector("q", "fake", "v1", "publico", [1.0, 0.0])
    assert load_vector("q", "fake", "v1", "publico") == [1.0, 0.0]
    assert load_vector("q", "fake", "v1", "interno") is None
    assert is_restricted("sigiloso")


def test_metricas_p50_p95():
    reg = MetricsRegistry()
    for value in (10, 20, 30, 40, 100):
        reg.observe_latency_ms(value)
    snap = reg.snapshot()
    assert snap["latency_ms_p50"] == 30
    assert snap["latency_ms_p95"] == 100
