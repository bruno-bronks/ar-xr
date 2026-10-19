#!/usr/bin/env sh
# Sobe o Compose, espera ficar saudavel e roda os testes de integracao contra o ambiente real.
# Uso: ./scripts/smoke.sh [--keep]
set -eu
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe

docker compose up --build --wait --wait-timeout 180 || { docker compose logs --no-color; exit 1; }
code=0
BASE_URL="http://127.0.0.1:${API_PORT:-8088}" "$PY" -m pytest -q tests/integration || code=$?
[ "${1:-}" = "--keep" ] || docker compose down
exit $code
