#!/usr/bin/env bash
# Backup diário do piloto (RPO ≤ 24h).
# Uso típico (crontab): 0 2 * * * /caminho/licitai/scripts/backup_daily.sh >> /var/log/licitai-backup.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# Prefer dump via container Compose (evita falha de auth no host).
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${ROOT}/backups/licitai_${STAMP}"
mkdir -p "$OUT"

if docker compose ps --status running 2>/dev/null | grep -q sei-db; then
  echo "==> pg_dump via docker (sei-db)"
  docker exec sei-db pg_dump -U "${POSTGRES_USER:-sei_user}" -d "${POSTGRES_DB:-sei_analise}" \
    --format=custom -f /tmp/db.dump
  docker cp sei-db:/tmp/db.dump "$OUT/db.dump"
  docker exec sei-db rm -f /tmp/db.dump
else
  echo "==> fallback scripts/backup.sh"
  DATABASE_URL="${DATABASE_URL:-}" "$ROOT/backend/scripts/backup.sh" "$ROOT/backups"
  exit 0
fi

if [[ -d "$ROOT/backend/uploads" ]]; then
  tar -czf "$OUT/uploads.tar.gz" -C "$ROOT/backend" uploads
fi

cat > "$OUT/manifest.json" <<EOF
{
  "created_at": "${STAMP}",
  "method": "scripts/backup_daily.sh",
  "files": ["db.dump", "uploads.tar.gz"]
}
EOF

# Retenção: últimos 14
ls -1dt "$ROOT"/backups/licitai_* 2>/dev/null | tail -n +15 | xargs -r rm -rf

echo "OK: $OUT"
