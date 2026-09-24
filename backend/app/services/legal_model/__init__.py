"""Modelo jurídico versionado (Fase 4). Índice legado permanece ativo."""

from app.services.legal_model.compare import compare_sample
from app.services.legal_model.migrate import migrate_sample
from app.services.legal_model.persist import upsert_versioned_work
from app.services.legal_model.provisions import parse_provisions
from app.services.legal_model.query import ancestors_and_related, list_provisions

__all__ = [
    "parse_provisions",
    "upsert_versioned_work",
    "migrate_sample",
    "compare_sample",
    "list_provisions",
    "ancestors_and_related",
]
