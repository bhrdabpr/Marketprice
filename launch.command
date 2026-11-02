#!/bin/sh
set -eu
cd "$(dirname "$0")"
PYTHON="${MARKETPRICE_PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
fi
exec "$PYTHON" launcher.py "$@"
