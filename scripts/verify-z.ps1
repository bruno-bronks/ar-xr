# Parse + typecheck das specs Z com CZT (Community Z Tools). Requer JDK e czt.jar (ver docs/decisions/tool-evaluation.md).
# Variaveis: JAVA_EXE, CZT_JAR (padroes em %USERPROFILE%\.tools).
param([string[]]$Files = @(Get-ChildItem specs\formal-z\*.tex | ForEach-Object { $_.FullName }))
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$tools = Join-Path $env:USERPROFILE ".tools"
$java = if ($env:JAVA_EXE) { $env:JAVA_EXE } else { Get-ChildItem "$tools\jdk-*\bin\java.exe" | Select-Object -First 1 -ExpandProperty FullName }
$czt = if ($env:CZT_JAR) { $env:CZT_JAR } else { "$tools\czt\czt.jar" }
if (-not (Test-Path $java) -or -not (Test-Path $czt)) { Write-Host "JDK/CZT ausentes (veja tool-evaluation.md)"; exit 2 }

$failed = 0
foreach ($f in $Files) {
  $name = Split-Path $f -Leaf
  $out = cmd /c "`"$java`" -jar `"$czt`" `"$f`" 2>&1" | Out-String
  # Sucesso = sem excecao E linha "0 warnings and errors" (relatorio do typechecker).
  $clean = ($out -notmatch "Exception") -and ($out -match "(?m)^\s*0 warnings and errors")
  if ($LASTEXITCODE -ne 0 -or -not $clean) {
    Write-Host "FALHOU: $name"; Write-Host $out; $failed++
  } else { Write-Host "OK (parse+typecheck, 0 warnings and errors): $name" }
}
exit $failed
