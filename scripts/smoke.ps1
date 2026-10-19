# Sobe o Compose, espera ficar saudavel e roda os testes de integracao contra o ambiente real.
param([switch]$KeepRunning)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$port = if ($env:API_PORT) { $env:API_PORT } else { "8088" }
docker compose up --build --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { docker compose logs --no-color; exit 1 }

$env:BASE_URL = "http://127.0.0.1:$port"
.\.venv\Scripts\python.exe -m pytest -q tests/integration
$code = $LASTEXITCODE
if (-not $KeepRunning) { docker compose down }
exit $code
