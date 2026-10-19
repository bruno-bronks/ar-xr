#!/usr/bin/env sh
# Gates locais: lint, formato, tipos e testes (sem Docker).
set -eu
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe

echo "==> ruff check";    "$PY" -m ruff check .
echo "==> ruff format";   "$PY" -m ruff format --check .
echo "==> mypy (strict)"; "$PY" -m mypy
echo "==> pytest";        "$PY" -m pytest -q
echo "==> pip-audit";     "$PY" -m pip_audit -r services/api/requirements.txt --no-deps --disable-pip
echo "Todos os gates locais passaram."
