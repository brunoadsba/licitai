#!/usr/bin/env bash
# Alertas mínimos do piloto (sem K8s/CI).
# Uso: ./scripts/ops_alerts.sh [API_URL]
# Cron sugerido: */5 * * * * /caminho/licitai/scripts/ops_alerts.sh
set -euo pipefail

API="${1:-http://127.0.0.1:8000}"
LOG_DIR="${LICITAI_ALERT_LOG:-/tmp}"
STATE_FILE="${LICITAI_ALERT_STATE:-$LOG_DIR/licitai-alerts.state}"
LLM_DELTA_ALERT="${LICITAI_LLM_ERROR_DELTA:-3}"
COST_USD_ALERT="${LICITAI_COST_USD_ALERT:-1}"
mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ALERT=0

ready="$(curl -sS -m 5 "${API}/readyz" || echo '{}')"
status="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('status',''))" "$ready" 2>/dev/null || echo fail)"

if [[ "$status" != "ready" ]]; then
  echo "[$STAMP] ALERT readyz=$status body=$ready" | tee -a "$LOG_DIR/licitai-alerts.log"
  ALERT=1
fi

metrics="$(curl -sS -m 5 "${API}/metrics" || echo '{}')"
llm_errors="$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
c=d.get('counters') or {}
print(int(c.get('llm_errors', d.get('llm_errors', 0) or 0)))
" "$metrics" 2>/dev/null || echo 0)"

prev=0
if [[ -f "$STATE_FILE" ]]; then
  prev="$(python3 -c "import json; print(int(json.load(open('$STATE_FILE')).get('llm_errors',0)))" 2>/dev/null || echo 0)"
fi
delta=$((llm_errors - prev))
if (( delta < 0 )); then delta=$llm_errors; fi

python3 -c "import json; json.dump({'llm_errors': int('$llm_errors'), 'updated_at': '$STAMP'}, open('$STATE_FILE','w'))"

if (( delta >= LLM_DELTA_ALERT )); then
  echo "[$STAMP] ALERT llm_errors delta=${delta} total=${llm_errors} (threshold=${LLM_DELTA_ALERT})" | tee -a "$LOG_DIR/licitai-alerts.log"
  ALERT=1
fi

cost_usd="$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
print(float(d.get('cost_usd') or (d.get('counters') or {}).get('cost_usd') or 0))
" "$metrics" 2>/dev/null || echo 0)"

cost_over=0
if ! python3 -c "
cost=float('$cost_usd')
limit=float('$COST_USD_ALERT')
raise SystemExit(0 if cost < limit else 1)
"; then
  cost_over=1
fi

if (( cost_over == 1 )); then
  echo "[$STAMP] ALERT cost_usd=${cost_usd} (threshold=${COST_USD_ALERT})" | tee -a "$LOG_DIR/licitai-alerts.log"
  ALERT=1
fi

if (( ALERT == 0 )); then
  echo "[$STAMP] OK readyz=ready llm_errors=${llm_errors} delta=${delta} cost_usd=${cost_usd}" >> "$LOG_DIR/licitai-alerts.log"
  echo "OK ready=${status} llm_errors=${llm_errors} delta=${delta} cost_usd=${cost_usd}"
  exit 0
fi

echo "ALERT active (see $LOG_DIR/licitai-alerts.log)"
exit 2
