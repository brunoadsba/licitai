#!/usr/bin/env bash
# E2E rápido local (sem LLM longo). Exige API_TOKEN do .env.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a && source .env && set +a
test -n "${API_TOKEN:-}" || { echo "API_TOKEN vazio — copie .env.example para .env"; exit 1; }
E2E_BASE_URL="${E2E_BASE_URL:-http://127.0.0.1:8000}" PYTHONPATH=backend:e2e/tests \
  backend/.venv/bin/python -m pytest e2e/tests -m e2e_fast -v --tb=short "$@"
