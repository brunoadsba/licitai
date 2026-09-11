"""E2E fast: auth header quando API_TOKEN está definido."""

from __future__ import annotations

import os

import httpx
import pytest

from helpers import BASE_URL, api_headers

pytestmark = pytest.mark.e2e_fast


def test_api_token_optional_or_enforced():
    token = os.getenv("E2E_API_TOKEN") or os.getenv("API_TOKEN") or ""
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        bare = client.get("/api/v1/moldes")
        if not token:
            # Piloto local sem token: 200
            assert bare.status_code == 200, bare.text
            return
        # Com token no ambiente: sem header deve falhar; com header ok
        assert bare.status_code in (401, 403), bare.text
        ok = client.get("/api/v1/moldes", headers=api_headers())
        assert ok.status_code == 200, ok.text
