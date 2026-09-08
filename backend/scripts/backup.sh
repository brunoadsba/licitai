#!/usr/bin/env bash
# Backup operacional: pg_dump + tar dos uploads.
# Uso: ./scripts/backup.sh [DEST_DIR]
# Requer: DATABASE_URL (postgres) ou PG* env; UPLOAD_DIR opcional.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="${1:-${ROOT}/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${DEST}/licitai_${STAMP}"
mkdir -p "${OUT}"

UPLOAD_DIR="${UPLOAD_DIR:-${ROOT}/backend/uploads}"
DATABASE_URL="${DATABASE_URL:-}"

echo "==> Backup para ${OUT}"

if [[ -z "${DATABASE_URL}" ]]; then
  echo "WARN: DATABASE_URL vazio — pulando pg_dump" >&2
else
  # Converte SQLAlchemy URL → formato pg_dump quando necessário
  PGURL="${DATABASE_URL}"
  PGURL="${PGURL/#postgresql+asyncpg:/postgresql:}"
  PGURL="${PGURL/#postgres+asyncpg:/postgresql:}"
  PGURL="${PGURL/#postgresql+psycopg:/postgresql:}"
  echo "==> pg_dump"
  pg_dump --format=custom --file="${OUT}/db.dump" "${PGURL}"
fi

if [[ -d "${UPLOAD_DIR}" ]]; then
  echo "==> tar uploads (${UPLOAD_DIR})"
  tar -czf "${OUT}/uploads.tar.gz" -C "$(dirname "${UPLOAD_DIR}")" "$(basename "${UPLOAD_DIR}")"
else
  echo "WARN: UPLOAD_DIR ausente (${UPLOAD_DIR}) — pulando tar" >&2
fi

# Manifesto
cat > "${OUT}/manifest.json" <<EOF
{
  "created_at": "${STAMP}",
  "database_url_redacted": true,
  "upload_dir": "${UPLOAD_DIR}",
  "files": ["db.dump", "uploads.tar.gz"]
}
EOF

# Retenção simples: mantém últimos 14 diretórios
ls -1dt "${DEST}"/licitai_* 2>/dev/null | tail -n +15 | xargs -r rm -rf

echo "OK: ${OUT}"
