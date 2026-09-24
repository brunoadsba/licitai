#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --quiet pip-audit
python -m pip_audit -r requirements.txt
