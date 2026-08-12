# Pomelo K8s Deployment Script
#
# Usage:
#   .\deploy\k8s\deploy.ps1 test [TAG]     # deploy to test env (mb-test)
#   .\deploy\k8s\deploy.ps1 prod [TAG]     # deploy to prod env (mb-pr)
#   .\deploy\k8s\deploy.ps1 test -CreateSecret  # also create/update secrets from envs
#
# Prerequisites:
#   kubectl configured (C:\green\kubectl.exe)
#   docker image already pushed to ACR

param(
    [ValidateSet("test", "prod")]
    [string]$Env = "test",

    [string]$Tag = $null,

    [switch]$CreateSecret = $false
)

$ErrorActionPreference = "Stop"
$KUBECTL = "C:\green\kubectl.exe"

if (-not $Tag) {
    $Tag = & git -C "$PSScriptRoot\..\.." rev-parse --short HEAD
}

$CFG = @{
    test = @{
        NS         = "mb-test"
        Domain     = "pomelo.dev.youbanban.com"
        OSSBucket  = "pomelo-mb-test"
        OSSIP      = "47.102.237.237"
    }
    prod = @{
        NS         = "mb-pr"
        Domain     = "pomelo.youbanban.com"
        OSSBucket  = "pomelo-mb-prod"
        OSSIP      = "106.14.228.188"
    }
}

$c = $CFG[$Env]
$NS     = $c.NS
$Domain = $c.Domain
$OSS    = $c.OSSBucket

$TAG_PLACEHOLDER      = "<TAG>"
$NS_PLACEHOLDER       = "<NAMESPACE>"
$DOMAIN_PLACEHOLDER   = "<DOMAIN>"
$OSS_PLACEHOLDER      = "<OSS_BUCKET>"
$OSSIP_PLACEHOLDER    = "<OSS_IP>"

$YAMLS = @(
    "$PSScriptRoot\namespace.yaml",
    "$PSScriptRoot\certificate.yaml",
    "$PSScriptRoot\pv-nas.yaml",
    "$PSScriptRoot\oss-webui.yaml",
    "$PSScriptRoot\oss-webui-plugin.yaml",
    "$PSScriptRoot\backend\service.yaml",
    "$PSScriptRoot\backend\deployment.yaml",
    "$PSScriptRoot\ingress.yaml"
)

Write-Host "`nDeploying to $Env (namespace=$NS, domain=$Domain)" -ForegroundColor Cyan
Write-Host "Image tag: $Tag`n"

if ($CreateSecret) {
    $envFile = Join-Path $PSScriptRoot "..\..\deploy\envs\$Env.env"
    if (Test-Path $envFile) {
        Write-Host "Creating / updating secret from $envFile ..." -ForegroundColor Yellow
        $lines = Get-Content $envFile | Where-Object { $_ -match '^\s*(\S+)\s*=\s*(.*)' }
        $args = @("-n", $NS, "create", "secret", "generic", "pomelo-secrets", "--dry-run=client", "-o", "yaml")
        foreach ($line in $lines) {
            if ($line -match '^\s*(\S+)\s*=\s*(.*)') {
                $key = $Matches[1].Trim()
                $val = $Matches[2].Trim()
                $args += "--from-literal=$key=$val"
            }
        }
        $yaml = & $KUBECTL @args 2>&1
        if ($LASTEXITCODE -eq 0) {
            $yaml | & $KUBECTL apply -f -
            Write-Host "Secret pomelo-secrets updated in $NS" -ForegroundColor Green
        } else {
            Write-Host "Warning: failed to generate secret YAML: $yaml" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Warning: env file not found at $envFile" -ForegroundColor Yellow
    }
}

$tmpDir = Join-Path $env:TEMP "pomelo-deploy-$Env"
Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

foreach ($src in $YAMLS) {
    $name = Split-Path $src -Leaf
    $content = Get-Content $src -Raw
    $content = $content.Replace($TAG_PLACEHOLDER, $Tag)
    $content = $content.Replace($NS_PLACEHOLDER, $NS)
    $content = $content.Replace($DOMAIN_PLACEHOLDER, $Domain)
    $content = $content.Replace($OSS_PLACEHOLDER, $OSS)
    $content = $content.Replace($OSSIP_PLACEHOLDER, $c.OSSIP)
    $out = Join-Path $tmpDir $name
    Set-Content -Path $out -Value $content -NoNewline
    Write-Host "  $name"
    & $KUBECTL apply -f $out
}

Write-Host "`nDone. Check pods:" -ForegroundColor Green
Write-Host "  kubectl get pods -n $NS"
