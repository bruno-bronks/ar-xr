# Obtem zxing.unity.dll do pacote NuGet oficial ZXing.Net (Apache-2.0) para o projeto Unity.
# Por que um script: o proxy corporativo do desenvolvedor bloqueia download de .nupkg ("File Transfer Blocked").
# Rode em uma rede SEM esse bloqueio (ou baixe o .nupkg la e passe -NupkgPath).
# O hash do .nupkg e PINADO: se nao conferir, o script recusa (nao desabilita nada).
param(
  [string]$NupkgPath = "",
  [string]$Version = "0.16.9",
  # Preenchido a partir da saida do job `csharp` da CI (passo "ZXing.Net package facts"). Vazio = recusa.
  [string]$ExpectedSha256 = ""
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $ExpectedSha256) { throw "ExpectedSha256 nao configurado: veja docs/runbooks/ar-device-checklist.md (secao 0) e a CI." }

$tmp = Join-Path $env:TEMP "zxing-$Version"; New-Item -ItemType Directory -Force $tmp | Out-Null
if (-not $NupkgPath) {
  $NupkgPath = Join-Path $tmp "zxing.net.$Version.nupkg"
  Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/zxing.net/$Version/zxing.net.$Version.nupkg" -OutFile $NupkgPath
}
$hash = (Get-FileHash $NupkgPath -Algorithm SHA256).Hash.ToLower()
if ($hash -ne $ExpectedSha256.ToLower()) { throw "SHA-256 diferente do pinado ($hash). Abortado." }

Expand-Archive $NupkgPath -DestinationPath "$tmp\x" -Force
$dll = Get-ChildItem "$tmp\x\lib\unity\*.dll" | Select-Object -First 1
if (-not $dll) { throw "lib/unity/*.dll ausente no pacote" }
$dest = "clients\ar-unity\Assets\Plugins\ZXing"; New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item $dll.FullName "$dest\zxing.unity.dll" -Force
Write-Host "OK: $dest\zxing.unity.dll (de $($dll.Name))"
