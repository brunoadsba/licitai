#!/usr/bin/env bash
# Para a stack Compose sem apagar volumes (pgdata preservado).
# Uso: ./scripts/down.sh
#
# NÃO aceita -v / --volumes. Reset deliberado de dados:
#   docker compose down -v
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -gt 0 ]]; then
  case "$1" in
    -v|--volumes|-h|--help)
      cat <<'EOF' >&2
Uso: ./scripts/down.sh

Para containers e redes; mantém o volume pgdata.

Para apagar dados locais (irreversível neste host):
  docker compose down -v
EOF
      if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        exit 0
      fi
      echo "Recusado: este script não remove volumes." >&2
      exit 1
      ;;
    *)
      echo "Flag desconhecida: $1 (use --help)" >&2
      exit 1
      ;;
  esac
fi

echo "==> compose down (sem -v; pgdata preservado)"
docker compose down
echo "OK down"
