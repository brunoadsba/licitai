#!/usr/bin/env bash
# Auditoria mensal de dependências (Fase 6.3): npm audit + pip-audit.
# Salva relatório datado em docs/ops/audits/. Só reporta — nunca altera nada.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/ops/audits/$(date +%F).md"
mkdir -p "$ROOT/docs/ops/audits"
{
  echo "# Auditoria de dependências — $(date +%F)"
  echo
  echo "## Frontend (npm audit --omit=dev)"
  echo '```'
  (cd "$ROOT/frontend" && npm audit --omit=dev 2>&1 | tail -6)
  echo '```'
  echo
  echo "## Backend (pip-audit; exit!=0 significa 'achou algo', não erro)"
  echo '```'
  (cd "$ROOT/backend" && (pip-audit -r requirements.txt 2>&1; true) | sort -u | tail -20)
  echo '```'
} > "$OUT"
echo "Relatório: $OUT"
