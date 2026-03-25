Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Sam = "C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"

if (-not (Test-Path $Sam)) {
    throw "SAM CLI was not found at $Sam"
}

Push-Location $Root
try {
    & $Sam validate --template-file template.yaml --region ap-southeast-1
    & $Sam build --template-file template.yaml --region ap-southeast-1
    & $Sam deploy --guided --region ap-southeast-1
}
finally {
    Pop-Location
}
