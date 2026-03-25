param(
    [string]$Region = "ap-southeast-1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Sam = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"

if (-not (Test-Path $Sam)) {
    throw "SAM CLI was not found at $Sam"
}

Push-Location $Root
try {
    & $Sam validate --template-file template.yaml --region $Region
    & $Sam build --template-file template.yaml --region $Region
    & $Sam deploy --guided --region $Region
}
finally {
    Pop-Location
}
