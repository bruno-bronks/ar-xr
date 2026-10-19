#!/usr/bin/env sh
# Cria .venv e instala dependencias de desenvolvimento (Linux/macOS/Git Bash).
set -eu
cd "$(dirname "$0")/.."

[ -d .venv ] || python3 -m venv .venv
PY=.venv/bin/python
[ -x "$PY" ] || PY=.venv/Scripts/python.exe   # Git Bash no Windows
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r services/api/requirements.txt
"$PY" -m pip install --group dev
[ -f .env ] || { cp .env.example .env; echo ".env criado a partir de .env.example"; }
echo "Pronto. Rode: ./scripts/check.sh"
