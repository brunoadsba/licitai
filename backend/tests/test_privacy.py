"""Testes da política de privacidade cloud × documentos sigilosos."""

import pytest

from app.config import settings
from app.services.privacy import (
    CloudPrivacyError,
    assert_cloud_allowed_for_document,
    is_sigiloso,
    resolve_classification,
)


def test_is_sigiloso():
    assert is_sigiloso("sigiloso") is True
    assert is_sigiloso("SIGILOSO") is True
    assert is_sigiloso("publico") is False
    assert is_sigiloso(None) is False


def test_resolve_classification_prioridade():
    assert resolve_classification(
        form_value="sigiloso",
        header_value="publico",
        document_classification="outro",
    ) == "sigiloso"
    assert resolve_classification(
        header_value="Sigiloso",
        document_classification="publico",
    ) == "sigiloso"


def test_assert_cloud_bloqueia_quando_desabilitado(monkeypatch):
    monkeypatch.setattr(settings, "llm_allow_cloud", False)
    monkeypatch.setattr(settings, "llm_provider", "groq")
    with pytest.raises(CloudPrivacyError):
        assert_cloud_allowed_for_document("sigiloso")


def test_assert_cloud_permite_quando_flag_true(monkeypatch):
    monkeypatch.setattr(settings, "llm_allow_cloud", True)
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert_cloud_allowed_for_document("sigiloso")


def test_assert_cloud_permite_ollama(monkeypatch):
    monkeypatch.setattr(settings, "llm_allow_cloud", False)
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    assert_cloud_allowed_for_document("sigiloso")
