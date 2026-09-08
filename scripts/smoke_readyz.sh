#!/usr/bin/env bash
# Smoke local de readiness (sem CI). Uso: ./scripts/smoke_readyz.sh [BASE_URL]
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"

echo "==> livez"
curl -fsS "$BASE/livez" | tee /tmp/licitai_livez.json
echo
echo "==> readyz"
code=$(curl -sS -o /tmp/licitai_readyz.json -w "%{http_code}" "$BASE/readyz" || true)
cat /tmp/licitai_readyz.json
echo
if [[ "$code" != "200" ]]; then
  echo "readyz HTTP $code (esperado 200 após alembic upgrade head)" >&2
  exit 1
fi
echo "OK smoke readiness"
