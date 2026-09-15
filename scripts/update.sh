#!/usr/bin/env bash
# Update seguro do piloto: backup antes, migrate só se head mudou, smoke no fim.
# Uso: ./scripts/update.sh [--help] [--dry-run]
set -euo pipefail

dry_run=0
if [[ "${1:-}" == "--help" ]]; then
  echo "Uso: ./scripts/update.sh [--dry-run]"
  echo "  1) backup do banco (scripts/backup.sh, se existir)"
  echo "  2) git pull --ff-only"
  echo "  3) alembic upgrade head (só se houver migrations novas)"
  echo "  4) ./scripts/smoke_readyz.sh"
  echo "Rollback: restore do backup (nunca apaga pgdata)."
  exit 0
fi
[[ "${1:-}" == "--dry-run" ]] && dry_run=1

run() { if [[ "$dry_run" == "1" ]]; then echo "[dry-run] $*"; else eval "$@"; fi; }

if [[ -x backend/scripts/backup.sh ]]; then
  run "backend/scripts/backup.sh"
else
  echo "aviso: backend/scripts/backup.sh ausente — faça backup manual antes."
fi
run "git pull --ff-only"
if [[ -d backend/alembic ]]; then
  run "PYTHONPATH=backend backend/.venv/bin/python -m alembic -c backend/alembic.ini upgrade head || PYTHONPATH=backend python3 -m alembic -c backend/alembic.ini upgrade head"
fi
run "./scripts/smoke_readyz.sh"
echo "update ok."
