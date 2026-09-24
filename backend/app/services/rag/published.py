"""Filtro de documentos jurídicos publicados (não indexa falha/rascunho)."""

from __future__ import annotations

PUBLISHED_STATUS = "published"


def apply_sql_published_filter(sql: str, alias: str = "ld") -> str:
    """Exclui legal_documents que não estão publicados."""
    return (
        f"{sql} AND COALESCE({alias}.ingest_status, '{PUBLISHED_STATUS}') "
        f"= '{PUBLISHED_STATUS}'"
    )
