# Pomelo Frontend: Build Nuxt SSG & Upload to OSS
#
# Usage:
#   .\deploy\oss-upload.ps1          # upload to test bucket (pomelo-mb-test)
#   .\deploy\oss-upload.ps1 prod     # upload to prod bucket (pomelo-mb-prod)
#
# Prerequisites:
#   ossutil config -e oss-cn-shanghai.aliyuncs.com -i <AK> -k <SK>

param(
    [ValidateSet("test", "prod")]
    [string]$Env = "test"
)

$ErrorActionPreference = "Stop"

$OSSUTIL = "C:\green\ossutil.exe"

$DOMAINS = @{
    test = "https://pomelo.dev.youbanban.com"
    prod = "https://pomelo.youbanban.com"
}
$BUCKETS = @{
    test = "pomelo-mb-test"
    prod = "pomelo-mb-prod"
}
$Bucket = $BUCKETS[$Env]
$ApiBase = "$($DOMAINS[$Env])/api"

Write-Host "Building frontend for $Env (apiBase=$ApiBase) ..."

Push-Location "$PSScriptRoot\..\frontend"
try {
    $env:NUXT_PUBLIC_API_BASE = $ApiBase
    pnpm install
    pnpm generate
} finally {
    Pop-Location
}

Write-Host "Uploading to oss://$Bucket/ ..."
& $OSSUTIL cp -r "$PSScriptRoot\..\frontend\.output\public\" "oss://${Bucket}/" --update

Write-Host "Done: oss://$Bucket/"
