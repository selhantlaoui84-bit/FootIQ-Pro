#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level warning
