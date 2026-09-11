#!/usr/bin/env bash
# Sobe a stack Compose com env limpo (evita override WSL) e smoke de readiness.
# Uso: ./scripts/up.sh [--build] [--e2e] [--no-smoke]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUILD=0
SMOKE="readyz"

usage() {
  cat <<'EOF'
Uso: ./scripts/up.sh [--build] [--e2e] [--no-smoke]

  (padrão)     docker compose up -d + smoke_readyz.sh
  --build      up -d --build (necessário após mudança de UI/imagem)
  --e2e        após o up, roda smoke_e2e_compose.sh (readyz + BFF)
  --no-smoke   só sobe; não roda smoke

Antes do compose: unset POSTGRES_PASSWORD DATABASE_URL
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) BUILD=1 ;;
    --e2e) SMOKE="e2e" ;;
    --no-smoke) SMOKE="none" ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Flag desconhecida: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

# Evita POSTGRES_PASSWORD/DATABASE_URL sujos do shell (CRLF no WSL) sobrescreverem o .env
unset POSTGRES_PASSWORD DATABASE_URL || true

echo "==> compose up (env limpo)"
if [[ "$BUILD" -eq 1 ]]; then
  docker compose up -d --build
else
  docker compose up -d
fi

case "$SMOKE" in
  readyz)
    echo "==> smoke readiness"
    "$ROOT/scripts/smoke_readyz.sh"
    ;;
  e2e)
    echo "==> smoke E2E Compose (Camada 0)"
    "$ROOT/scripts/smoke_e2e_compose.sh"
    ;;
  none)
    echo "==> smoke omitido (--no-smoke)"
    ;;
esac

echo "OK up"
echo "  UI:  http://127.0.0.1:3000/"
echo "  API: http://127.0.0.1:8000/"
