"""Testes do stub de feedback thumbs-down → golden."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.feedback_golden import append_thumbs_down_stub


def test_append_thumbs_down_cria_stub(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "app.services.feedback_golden._FEEDBACK_DIR",
        tmp_path,
    )
    path = append_thumbs_down_stub(
        message_id=42,
        content="resposta assistente",
        comment="ruim",
        conversation_id=7,
        sources=[{"id": "s1"}],
    )
    assert path is not None
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["kind"] == "chat_thumbs_down"
    assert data["message_id"] == 42
    assert data["status"] == "stub"
    assert "Promover" in data["notes"]
