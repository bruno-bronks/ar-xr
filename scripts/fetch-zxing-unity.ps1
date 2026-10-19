# Obtem zxing.dll (build netstandard2.1 - a MESMA usada nos testes da CI) do pacote NuGet oficial ZXing.Net
# (Apache-2.0) para o projeto Unity 6. O pacote 0.16.9 NAO tem pasta lib/unity (verificado na CI): usa-se
# lib/netstandard2.1.
#
# Por que um script: o proxy corporativo do desenvolvedor bloqueia download de .nupkg ("File Transfer Blocked").
# Rode em uma rede SEM esse bloqueio, ou baixe o .nupkg la e passe -NupkgPath.
# O SHA-256 do .nupkg e PINADO: se nao conferir, o script recusa (nao desabilita nenhuma verificacao).
param(
  [string]$NupkgPath = "",
  [string]$Version = "0.16.9",
  # SHA-256 do zxing.net.0.16.9.nupkg observado no job `csharp` da CI (restore do nuget.org).
  [string]$ExpectedSha256 = "00254acaaea069262e6b103d23f1a934e953d503ea43afe2965272718388f32e"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$tmp = Join-Path $env:TEMP "zxing-$Version"
New-Item -ItemType Directory -Force $tmp | Out-Null
if (-not $NupkgPath) {
  $NupkgPath = Join-Path $tmp "zxing.net.$Version.nupkg"
  Invoke-WebRequest "https://api.nuget.org/v3-flatcontainer/zxing.net/$Version/zxing.net.$Version.nupkg" -OutFile $NupkgPath
}
$hash = (Get-FileHash $NupkgPath -Algorithm SHA256).Hash.ToLower()
if ($hash -ne $ExpectedSha256.ToLower()) { throw "SHA-256 diferente do pinado ($hash). Abortado." }

$extract = Join-Path $tmp "x"
Expand-Archive $NupkgPath -DestinationPath $extract -Force
$dll = Join-Path $extract "lib\netstandard2.1\zxing.dll"
if (-not (Test-Path $dll)) { throw "lib/netstandard2.1/zxing.dll ausente no pacote" }

$dest = "clients\ar-unity\Assets\Plugins\ZXing"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item $dll (Join-Path $dest "zxing.dll") -Force
Write-Host "OK: $dest\zxing.dll (netstandard2.1, ZXing.Net $Version)"
