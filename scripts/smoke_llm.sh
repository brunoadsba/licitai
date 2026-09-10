#!/usr/bin/env bash
# Smoke pós-pin de modelo LLM (sem CI).
# Uso:
#   ./scripts/smoke_llm.sh              # FakeLLM / import path
#   LLM_SMOKE_REAL=1 ./scripts/smoke_llm.sh   # 1 generate real (gasta cota)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH=backend
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///:memory:}"
PY="${ROOT}/backend/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

echo "==> FakeLLM golden import"
"$PY" - <<'PY'
from app.services.analyzer import fake_llm_golden as m
assert hasattr(m, "fake_predict_findings")
print("OK fake_llm_golden.fake_predict_findings")
PY

if [[ "${LLM_SMOKE_REAL:-0}" == "1" ]]; then
  echo "==> LLM real ping (1 chamada)"
  set -a
  # shellcheck disable=SC1091
  [[ -f .env ]] && source .env
  set +a
  "$PY" - <<'PY'
import asyncio
from app.services.llm import get_llm_provider

async def main():
    llm = get_llm_provider()
    text = await llm.generate(
        system="Responda só OK.",
        user="Diga OK",
        temperature=0,
    )
    print("provider_ok", bool(text), "preview", (text or "")[:80])

asyncio.run(main())
PY
fi

echo "OK smoke_llm"
