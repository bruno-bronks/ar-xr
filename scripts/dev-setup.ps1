# Cria .venv e instala dependencias de desenvolvimento (Windows / PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r services/api/requirements.txt
.\.venv\Scripts\python.exe -m pip install --group dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host ".env criado a partir de .env.example" }
Write-Host "Pronto. Rode: .\scripts\check.ps1"
