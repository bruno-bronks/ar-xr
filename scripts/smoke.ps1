# Sobe o Compose (db, broker, migrate, api, worker, simulator), espera ficar saudavel e roda os testes
# contra a pilha REAL. -Quick: apenas o smoke de saude. -KeepRunning: nao derruba a pilha ao final.
param([switch]$Quick, [switch]$KeepRunning)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8088" }
$dbPort = if ($env:DB_PORT) { $env:DB_PORT } else { "55432" }
$dbPassword = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "spatial-dev-only" }
docker compose up --build --wait --wait-timeout 240
if ($LASTEXITCODE -ne 0) { docker compose logs --no-color; exit 1 }

$env:BASE_URL = "http://127.0.0.1:$apiPort"
$env:TEST_DATABASE_URL = "postgresql+psycopg://spatial:$dbPassword@127.0.0.1:$dbPort/spatial"
$targets = if ($Quick) { @("tests/integration/test_compose_smoke.py") } else { @("tests/integration", "tests/performance", "tests/e2e") }
.\.venv\Scripts\python.exe -m pytest -q @targets
$code = $LASTEXITCODE
if (-not $KeepRunning) { docker compose down }
exit $code
