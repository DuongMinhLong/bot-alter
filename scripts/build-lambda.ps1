Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PackageDir = Join-Path $Root ".aws-lambda-package"
$DistDir = Join-Path $Root "dist"
$ZipPath = Join-Path $DistDir "btc-alert-lambda.zip"

Write-Warning "Prefer building this package on Linux, WSL, Docker, or AWS CloudShell for Lambda runtime compatibility."

if (Test-Path $PackageDir) {
    Remove-Item $PackageDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir | Out-Null
}

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}
python -m pip install `
    --no-binary=:all: `
    -r (Join-Path $Root "requirements.txt") `
    -t $PackageDir
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Lambda dependencies."
}
Copy-Item (Join-Path $Root "src\\btc_alert_bot") $PackageDir -Recurse
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force

Write-Host "Lambda package created at $ZipPath"
