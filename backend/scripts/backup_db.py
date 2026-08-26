"""
Backup do banco SQLite usando a API de backup nativa (segura com WAL).

Funciona com o backend rodando: copia um snapshot consistente sem parar
o serviço e sem bloquear escritas por mais que alguns instantes.

Uso:
    python scripts/backup_db.py                     # ./licitacao.db -> ./backups/
    python scripts/backup_db.py --origem outro.db --destino /tmp/backups

Em produção, agende via cron (Linux/macOS) ou Agendador de Tarefas (Windows),
ex.: diariamente às 03:00:
    0 3 * * * cd /caminho/licitai/backend && .venv/bin/python scripts/backup_db.py

Para PostgreSQL, prefira pg_dump/pg_backup — este script é específico do SQLite.
"""

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def _caminho_sqlite(database_url: str) -> Path | None:
    prefixo = "sqlite:///"
    if not database_url.startswith(prefixo):
        return None
    return Path(database_url[len(prefixo):])


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup do banco SQLite")
    parser.add_argument("--origem", default=None, help="Arquivo .db de origem")
    parser.add_argument("--destino", default="backups", help="Diretório de destino")
    args = parser.parse_args()

    origem = (
        Path(args.origem)
        if args.origem
        else _caminho_sqlite(settings.database_url)
    )
    if origem is None:
        print("DATABASE_URL não é SQLite — use pg_dump para PostgreSQL.")
        return 1
    if not origem.exists():
        print(f"Banco de origem não encontrado: {origem}")
        return 1

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    arquivo = destino / f"{origem.stem}_{stamp}.db"

    conexao_origem = sqlite3.connect(origem)
    try:
        conexao_destino = sqlite3.connect(arquivo)
        try:
            conexao_origem.backup(conexao_destino)
        finally:
            conexao_destino.close()
    finally:
        conexao_origem.close()

    print(f"Backup criado: {arquivo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
