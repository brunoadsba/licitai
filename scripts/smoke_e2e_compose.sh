#!/usr/bin/env bash
# Smoke Compose + BFF para E2E full (Camada 0).
# Uso: ./scripts/smoke_e2e_compose.sh [API_URL] [FRONTEND_URL]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${1:-http://127.0.0.1:8000}"
FE="${2:-http://127.0.0.1:3000}"

echo "==> Camada 0: readiness"
"$ROOT/scripts/smoke_readyz.sh" "$API" "$FE"

check_proxy() {
  local name="$1" path="$2"
  local code body
  body=$(mktemp)
  code=$(curl -sS -o "$body" -w "%{http_code}" "$FE$path" || true)
  echo "==> BFF $name ($FE$path) HTTP $code"
  if [[ "$code" != "200" ]]; then
    head -c 400 "$body" || true
    echo
    rm -f "$body"
    echo "FALHA: BFF $name esperava HTTP 200 (possível /api/v1/v1/...)" >&2
    exit 1
  fi
  if grep -q '"detail":"Not Found"' "$body" 2>/dev/null; then
    rm -f "$body"
    echo "FALHA: BFF $name retornou Not Found" >&2
    exit 1
  fi
  rm -f "$body"
}

echo "==> Camada 0: BFF proxy lists"
check_proxy "documents" "/api/proxy/documents"
check_proxy "moldes" "/api/proxy/moldes"
check_proxy "comparison" "/api/proxy/comparison"
check_proxy "fornecedores" "/api/proxy/fornecedores"

# Regressão: path legado com /v1 no proxy não pode 404
code=$(curl -sS -o /dev/null -w "%{http_code}" "$FE/api/proxy/v1/moldes" || true)
echo "==> BFF legado /api/proxy/v1/moldes HTTP $code"
if [[ "$code" != "200" ]]; then
  echo "FALHA: strip de v1 no proxy quebrado" >&2
  exit 1
fi

echo "OK smoke E2E Compose (Camada 0)"
