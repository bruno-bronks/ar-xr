# Gates locais: lint, formato, tipos e testes (sem Docker). Falha ao primeiro gate vermelho.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$py = ".\.venv\Scripts\python.exe"

function Run($label, $args_) {
  Write-Host "==> $label"
  # stderr de ferramentas nativas (ex.: warnings do pip-audit) nao e falha: vale o exit code.
  $ErrorActionPreference = "Continue"
  & $py -m @args_
  $code = $LASTEXITCODE
  $ErrorActionPreference = "Stop"
  if ($code -ne 0) { Write-Host "FALHOU: $label"; exit $code }
}

Run "ruff check"        @("ruff", "check", ".")
Run "ruff format"       @("ruff", "format", "--check", ".")
Run "mypy (strict)"     @("mypy")
Run "pytest"            @("pytest", "-q")
Run "pip-audit"         @("pip_audit", "-r", "services/api/requirements.txt", "--no-deps", "--disable-pip")
Write-Host "Todos os gates locais passaram."
