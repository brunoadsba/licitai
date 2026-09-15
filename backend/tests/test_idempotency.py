from app.utils import idempotency as cache


def test_idempotency_store_lookup_evict():
    cache.clear()
    assert cache.lookup("k") is None
    cache.store("k", {"job_id": "1"})
    assert cache.lookup("k") == {"job_id": "1"}


def test_idempotency_same_key_returns_same_value():
    cache.clear()
    cache.store("analysis:doc1:key123", {"analysis_id": "a", "job_id": "j"})
    assert cache.lookup("analysis:doc1:key123")["job_id"] == "j"
    assert cache.lookup("analysis:doc1:outra") is None
