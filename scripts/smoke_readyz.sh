#!/usr/bin/env bash
# Smoke local de readiness (sem CI).
# Uso: ./scripts/smoke_readyz.sh [API_URL] [FRONTEND_URL]
set -euo pipefail
API="${1:-http://127.0.0.1:8000}"
FE="${2:-http://127.0.0.1:3000}"

check_json() {
  local name="$1" url="$2" expect_substr="${3:-}"
  local code body
  body=$(mktemp)
  code=$(curl -sS -o "$body" -w "%{http_code}" "$url" || true)
  echo "==> $name ($url) HTTP $code"
  # JSON curto; HTML só confirma status
  if head -c 1 "$body" | grep -q '{'; then
    cat "$body"
    echo
  fi
  if [[ "$code" != "200" ]]; then
    rm -f "$body"
    echo "FALHA: $name esperava HTTP 200" >&2
    exit 1
  fi
  if [[ -n "$expect_substr" ]] && ! grep -q "$expect_substr" "$body"; then
    rm -f "$body"
    echo "FALHA: $name sem '$expect_substr' no corpo" >&2
    exit 1
  fi
  rm -f "$body"
}

check_json "livez" "$API/livez" '"status":"alive"'
check_json "readyz" "$API/readyz" '"status":"ready"'
check_json "api/docs" "$API/api/docs"
check_json "frontend/" "$FE/"
check_json "frontend/readyz" "$FE/readyz" '"status":"ready"'

if command -v docker >/dev/null 2>&1; then
  echo "==> compose health"
  for c in sei-db sei-backend sei-worker sei-frontend; do
    st=$(docker inspect -f '{{.State.Health.Status}}' "$c" 2>/dev/null || echo "missing")
    echo "  $c: $st"
    if [[ "$st" != "healthy" && "$st" != "missing" ]]; then
      # worker/frontend podem ainda estar starting logo após up
      if [[ "$st" == "starting" ]]; then
        echo "  (ainda starting — ok no smoke imediato)"
      else
        echo "FALHA: $c health=$st" >&2
        exit 1
      fi
    fi
  done
fi

echo "OK smoke readiness"
