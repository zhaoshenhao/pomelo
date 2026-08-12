# Pomelo — One-time Environment Setup Script
# ============================================================================
# Usage:
#   .\deploy\scripts\create-env.ps1 test    # Setup mb-test namespace
#   .\deploy\scripts\create-env.ps1 prod    # Setup mb-pr namespace
#
# What it does:
#   1. Create namespace
#   2. Create regsecret (ACR pull secret)
#   3. Create pomelo-secrets (from deploy/envs/<env>.env)
#   4. Create NAS PV + PVC
#   5. Create OSS webui Service + Endpoints
# ============================================================================
param(
    [ValidateSet("test", "prod")]
    [string]$Env = "test",

    [string]$AcrUser = "",
    [string]$AcrPassword = ""
)

$ErrorActionPreference = "Stop"
$KUBECTL = "kubectl"

$CFG = @{
    test = @{ NS = "mb-test" }
    prod = @{ NS = "mb-pr"  }
}
$c = $CFG[$Env]
$NS = $c.NS

$NS_PLACEHOLDER  = "<NAMESPACE>"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pomelo One-Time Env Setup: $Env (namespace=$NS)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Namespace
Write-Host "`n[1/5] Creating namespace $NS ..." -ForegroundColor Yellow
$nsContent = (Get-Content "$PSScriptRoot\..\k8s\namespace.yaml" -Raw).Replace($NS_PLACEHOLDER, $NS)
$nsContent | & $KUBECTL apply -f -
Write-Host "  Namespace ready" -ForegroundColor Green

# 2. ACR regsecret
Write-Host "`n[2/5] Creating ACR pull secret (regsecret) ..." -ForegroundColor Yellow
if (-not $AcsUser) { $AcsUser = Read-Host "ACR username" }
if (-not $AcsPassword) { $AcsPassword = Read-Host "ACR password" -AsSecureString | ForEach-Object { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) } }
& $KUBECTL create secret docker-registry regsecret -n $NS `
    --docker-server=registry.cn-shanghai.aliyuncs.com `
    --docker-username=$AcsUser `
    --docker-password=$AcsPassword `
    --dry-run=client -o yaml | & $KUBECTL apply -f -
Write-Host "  regsecret created" -ForegroundColor Green

# 3. pomelo-secrets (from env file, via deploy.ps1 logic)
Write-Host "`n[3/5] Creating pomelo-secrets from deploy/envs/$Env.env ..." -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot ".." "envs" "$Env.env"
if (Test-Path $envFile) {
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
        Write-Host "  pomelo-secrets created (namespace=$NS)" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: failed to generate secret: $yaml" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: env file not found at $envFile — skipping secrets; run create-k8s-secrets.sh manually" -ForegroundColor Yellow
}

# 4. NAS PV + PVC
Write-Host "`n[4/5] Applying PV + PVC ..." -ForegroundColor Yellow
$pvContent = (Get-Content "$PSScriptRoot\..\k8s\pv-nas.yaml" -Raw).Replace($NS_PLACEHOLDER, $NS)
$pvContent | & $KUBECTL apply -f -
Write-Host "  PV + PVC applied" -ForegroundColor Green

# 5. OSS WebUI Service + Endpoints
Write-Host "`n[5/5] Applying OSS WebUI Service + Endpoints ..." -ForegroundColor Yellow
$ossContent = (Get-Content "$PSScriptRoot\..\k8s\oss-webui.yaml" -Raw).Replace($NS_PLACEHOLDER, $NS)
$ossContent | & $KUBECTL apply -f -
Write-Host "  OSS WebUI applied" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup complete for $Env (namespace=$NS)" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Create db-root-secret: kubectl -n $NS create secret generic pomelo-db-root-secret --from-literal=DB_ROOT_USER=root --from-literal=DB_ROOT_PASSWORD=<root-password>" -ForegroundColor White
Write-Host "  2. Edit init-db-job.yaml: replace <RDS_HOST> with actual host" -ForegroundColor White
Write-Host "  3. kubectl apply -f deploy/k8s/init-db-job.yaml" -ForegroundColor White
Write-Host "  4. .\deploy\k8s\deploy.ps1 $Env" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
