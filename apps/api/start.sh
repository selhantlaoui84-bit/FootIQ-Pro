#!/usr/bin/env bash
set -euo pipefail

if [ "${ENV:-development}" = "production" ] && [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is required when ENV=production" >&2
  exit 1
fi

PORT="${PORT:-8080}"
python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level warning
