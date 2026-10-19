#!/usr/bin/env sh
# Sobe o Compose e roda os testes contra a pilha REAL.
# Uso: ./scripts/smoke.sh [--quick] [--keep]
set -eu
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe

docker compose up --build --wait --wait-timeout 240 || { docker compose logs --no-color; exit 1; }
export BASE_URL="http://127.0.0.1:${API_PORT:-8088}"
export TEST_DATABASE_URL="postgresql+psycopg://spatial:${POSTGRES_PASSWORD:-spatial-dev-only}@127.0.0.1:${DB_PORT:-55432}/spatial"
targets="tests/integration tests/performance tests/e2e"
case " $* " in *" --quick "*) targets="tests/integration/test_compose_smoke.py" ;; esac
code=0
# shellcheck disable=SC2086
"$PY" -m pytest -q $targets || code=$?
case " $* " in *" --keep "*) ;; *) docker compose down ;; esac
exit $code
