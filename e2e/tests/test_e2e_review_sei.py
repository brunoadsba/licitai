"""E2E live: review humana + sei-pack + art6 (reusa analyzed_document)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e_live


def test_art6_fields_on_analysis(analyzed_document, api_client):
    analysis = analyzed_document["analysis"]
    assert "art6_checklist" in analysis or analysis.get("art6_coverage") is not None
    report = api_client.get(f"/api/v1/analysis/{analyzed_document['analysis_id']}/report")
    assert report.status_code == 200, report.text
    body = report.json()
    assert "art6_checklist" in body or body.get("art6_coverage") is not None


def test_review_unlocks_sei_pack(analyzed_document, api_client):
    analysis_id = analyzed_document["analysis_id"]
    analysis = analyzed_document["analysis"]
    corrections = analysis.get("corrections") or []
    if not corrections:
        pytest.skip("Análise sem correções — não dá para revisar")

    cid = corrections[0]["id"]
    before = api_client.get(f"/api/v1/analysis/{analysis_id}/sei-pack")
    # Pode ser 200 vazio ou 400 sem aprovadas — ambos ok antes
    assert before.status_code in (200, 400), before.text

    patch = api_client.patch(
        f"/api/v1/analysis/corrections/{cid}",
        json={"review_status": "aprovada"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["review_status"] == "aprovada"

    pack = api_client.get(f"/api/v1/analysis/{analysis_id}/sei-pack")
    assert pack.status_code == 200, pack.text
    body = pack.json()
    text = body.get("text") or ""
    assert len(text) > 10
    assert body.get("total", 0) >= 1 or "SEI" in text or "sugerido" in text.lower() or len(text) > 10
