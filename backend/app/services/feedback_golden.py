"""
Loop de feedback: thumbs-down do chat → stub golden em e2e/golden/feedback/.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# backend/app/services/feedback_golden.py → repo root = parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FEEDBACK_DIR = _REPO_ROOT / "e2e" / "golden" / "feedback"


def append_thumbs_down_stub(
    *,
    message_id: int,
    content: str,
    comment: str | None,
    conversation_id: int | None = None,
    sources: list | dict | None = None,
) -> Path | None:
    """
    Grava stub JSON para promoção posterior a caso golden.

    Retorna o path criado ou None se falhar (nunca propaga — feedback da API
    não deve quebrar por I/O de golden).
    """
    try:
        _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = _FEEDBACK_DIR / f"thumbs_down_{message_id}_{ts}.json"
        payload = {
            "kind": "chat_thumbs_down",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message_id": message_id,
            "conversation_id": conversation_id,
            "assistant_content": (content or "")[:4000],
            "comment": comment,
            "sources": sources or [],
            "status": "stub",
            "notes": "Promover manualmente para e2e/golden/ após curadoria humana.",
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("feedback.golden.stub path=%s", path)
        return path
    except Exception:
        logger.exception("feedback.golden.stub.failed message_id=%s", message_id)
        return None
