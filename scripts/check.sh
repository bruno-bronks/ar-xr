#!/usr/bin/env sh
# Gates locais: lint, formato, tipos e testes (sem Docker). Testes que exigem PostgreSQL/stack sao PULADOS
# (e aparecem como skipped) quando TEST_DATABASE_URL/BASE_URL nao estao definidos.
set -eu
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe

echo "==> ruff check";    "$PY" -m ruff check .
echo "==> ruff format";   "$PY" -m ruff format --check .
echo "==> mypy (strict)"; "$PY" -m mypy
echo "==> pytest";        "$PY" -m pytest -q
for svc in api telemetry-worker equipment-simulator; do
  echo "==> pip-audit ($svc)"
  "$PY" -m pip_audit -r "services/$svc/requirements.txt" --no-deps --disable-pip
done
echo "Todos os gates locais passaram."
