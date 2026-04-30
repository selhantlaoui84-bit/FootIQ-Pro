#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$REPO_ROOT"
sh scripts/setup_env.sh

if [ -n "${VIRTUAL_ENV:-}" ]; then
  PYTHON_BIN="python"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
else
  PYTHON_BIN="python"
fi

if [ -d ".python-packages" ]; then
  export PYTHONPATH="$REPO_ROOT/.python-packages${PYTHONPATH:+:$PYTHONPATH}"
fi

"$PYTHON_BIN" -m gunicorn -k uvicorn.workers.UvicornWorker apps.api.main:app -w "${WEB_CONCURRENCY:-2}" -b "0.0.0.0:${PORT:-8000}"
