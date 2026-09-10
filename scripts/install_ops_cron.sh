#!/usr/bin/env bash
# Instala entradas de cron do piloto (backup diário + alertas a cada 5 min).
# Uso:
#   ./scripts/install_ops_cron.sh           # mostra o bloco a adicionar
#   ./scripts/install_ops_cron.sh --apply   # adiciona ao crontab do usuário (idempotente)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

MARKER_BEGIN="# BEGIN LICITAI_OPS"
MARKER_END="# END LICITAI_OPS"
LOG_BACKUP="${LICITAI_BACKUP_LOG:-$ROOT/backups/backup_cron.log}"
LOG_ALERT="${LICITAI_ALERT_LOG:-/tmp}"

BLOCK=$(cat <<EOF
${MARKER_BEGIN}
# LicitAI piloto — gerado por scripts/install_ops_cron.sh
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * * ${ROOT}/scripts/backup_daily.sh >> ${LOG_BACKUP} 2>&1
*/5 * * * * LICITAI_ALERT_LOG=${LOG_ALERT} ${ROOT}/scripts/ops_alerts.sh http://127.0.0.1:8000 >> ${LOG_ALERT}/licitai-alerts-cron.log 2>&1
${MARKER_END}
EOF
)

echo "==> Bloco de cron (LICITAI_ROOT=${ROOT})"
echo "$BLOCK"
echo

if [[ "$APPLY" -ne 1 ]]; then
  echo "Dry-run. Para instalar no crontab do usuário atual:"
  echo "  ./scripts/install_ops_cron.sh --apply"
  exit 0
fi

mkdir -p "$(dirname "$LOG_BACKUP")" "$LOG_ALERT"
tmpdir=$(mktemp)
trap 'rm -f "$tmpdir"' EXIT

crontab -l 2>/dev/null | awk -v b="$MARKER_BEGIN" -v e="$MARKER_END" '
  $0==b {skip=1; next}
  $0==e {skip=0; next}
  !skip {print}
' > "$tmpdir" || true

printf '%s\n' "$BLOCK" >> "$tmpdir"
crontab "$tmpdir"
echo "OK: crontab atualizado (bloco ${MARKER_BEGIN} … ${MARKER_END})"
crontab -l | sed -n "/${MARKER_BEGIN}/,/${MARKER_END}/p"
