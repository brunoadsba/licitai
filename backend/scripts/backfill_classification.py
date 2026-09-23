"""Backfill da classificação de documentos ainda NULL.

Dry-run é o padrão. Só grava com --apply, e só em linhas cuja classificação
está NULL. Imprime os IDs afetados (guarde a lista para reverter o backfill).

Exemplos (a partir de backend/, com PYTHONPATH=.):

  python scripts/backfill_classification.py --to publico --all-null
  python scripts/backfill_classification.py --to interno --ids <uuid>,<uuid> --apply
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.privacy import normalize_classification

_ALLOWED = frozenset({"publico", "interno", "sigiloso"})


async def backfill_classification(
    session: AsyncSession,
    *,
    to: str,
    ids: list[str] | None,
    all_null: bool,
    apply: bool,
) -> list[str]:
    """Devolve os IDs NULL que seriam (ou foram) atualizados."""
    destino = normalize_classification(to)
    if destino not in _ALLOWED:
        raise ValueError("Valor de --to inválido. Use publico, interno ou sigiloso.")
    has_ids = bool(ids)
    if has_ids == all_null:
        raise ValueError("Informe --ids ou --all-null, exclusivamente.")

    stmt = select(Document).where(Document.classification.is_(None))
    if ids:
        stmt = stmt.where(Document.id.in_([uuid.UUID(item) for item in ids]))
    rows = (await session.execute(stmt)).scalars().all()
    changed = [str(row.id) for row in rows]
    if apply:
        for row in rows:
            row.classification = destino
        await session.commit()
    return changed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill de documents.classification NULL.")
    parser.add_argument("--to", required=True, help="publico, interno ou sigiloso")
    parser.add_argument("--ids", default="", help="UUIDs separados por vírgula")
    parser.add_argument("--all-null", action="store_true", help="Todos os documentos NULL")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava. Sem esta flag o comando só lista (dry-run).",
    )
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    ids = [item.strip() for item in args.ids.split(",") if item.strip()] or None
    from app.database import async_session_factory

    async with async_session_factory() as session:
        changed = await backfill_classification(
            session,
            to=args.to,
            ids=ids,
            all_null=args.all_null,
            apply=args.apply,
        )
    modo = "applied" if args.apply else "dry-run"
    print(f"{modo} count={len(changed)}")
    for item in changed:
        print(item)


if __name__ == "__main__":
    asyncio.run(_main())
