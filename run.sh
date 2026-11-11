#!/usr/bin/env bash
# Starts the Toolbox app. Usage: ./run.sh [port]
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8501}"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "No .venv found; using system Python. Run ./setup.sh first for a clean install."
fi

exec streamlit run app.py --server.port "$PORT" --server.address 127.0.0.1
