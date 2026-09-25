#!/usr/bin/env bash
# Monta o bloco FATOS DO GIT para colar na LLM junto com
# .cursor/contexts/auditoria-e2e-falhas.md
# Uso: ./scripts/contexto-auditoria.sh [--smoke]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SMOKE=0
if [[ "${1:-}" == "--smoke" ]]; then
  SMOKE=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Uso: ./scripts/contexto-auditoria.sh [--smoke]

Imprime o estado atual (branch, HEAD, status, stash, containers).
Cole a saída + o arquivo .cursor/contexts/auditoria-e2e-falhas.md numa LLM em Agent.

  --smoke   também roda ./scripts/smoke_readyz.sh (stack precisa estar up)
EOF
  exit 0
fi

echo "========================================"
echo "FATOS DO GIT — $(date -Iseconds)"
echo "========================================"
echo
echo "## branch / HEAD"
git branch --show-current
git log -1 --format='%h %s'
echo
echo "## branches recentes"
git branch -vv
echo
echo "## status"
git status -sb
echo
echo "## log (8)"
git log -8 --oneline
echo
echo "## stash"
git stash list || true
echo
echo "## containers (se Docker existir)"
if command -v docker >/dev/null 2>&1; then
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null \
    || echo "(compose indisponível)"
else
  echo "(docker não encontrado)"
fi
echo
if [[ "$SMOKE" -eq 1 ]]; then
  echo "## smoke_readyz"
  "$ROOT/scripts/smoke_readyz.sh" || true
  echo
fi

echo "========================================"
echo "PRÓXIMO PASSO"
echo "========================================"
echo "1. Abra uma conversa Agent."
echo "2. Cole o arquivo:"
echo "   $ROOT/.cursor/contexts/auditoria-e2e-falhas.md"
echo "3. Cole este bloco FATOS DO GIT abaixo do briefing."
echo "4. Peça: execute a missão do contexto. Não implemente feature."
echo
