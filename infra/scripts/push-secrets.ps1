# Push .env secrets to GitHub Secrets using GitHub CLI (gh)
param (
    [string]$EnvName = ""
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) is not installed or not in PATH."
    exit 1
}

$envPath = "infra/.env"
if (-not (Test-Path $envPath)) {
    $envPath = "infra/compose/.env"
}

if (-not (Test-Path $envPath)) {
    Write-Error "Could not find infra/.env file."
    exit 1
}

Write-Host "Reading $envPath..." -ForegroundColor Cyan

$bytes = [System.IO.File]::ReadAllBytes($envPath)
$b64 = [Convert]::ToBase64String($bytes)

$envArgs = @()
if ($EnvName) {
    $envArgs += @("--env", $EnvName)
    Write-Host "Targeting GitHub Environment: $EnvName" -ForegroundColor Yellow
} else {
    Write-Host "Targeting Repository-level secrets" -ForegroundColor Yellow
}

Write-Host "Setting DEPLOY_ENV_FILE_B64..." -NoNewline
$b64 | gh secret set DEPLOY_ENV_FILE_B64 @envArgs
Write-Host " [DONE]" -ForegroundColor Green

$raw = Get-Content $envPath -Raw
if ($raw -match 'DEPLOY_SSH_KEY_FILE=([^\r\n]+)') {
    $keyFile = $matches[1].Trim('"' + "'" + ' ')
    if (Test-Path $keyFile) {
        Write-Host "Setting DEPLOY_SSH_KEY from file ($keyFile)..." -NoNewline
        Get-Content $keyFile -Raw | gh secret set DEPLOY_SSH_KEY @envArgs
        Write-Host " [DONE]" -ForegroundColor Green
    }
} elseif ($raw -match 'DEPLOY_SSH_KEY=(["'']?)(-----BEGIN[^\1]+?-----END[^\1]+?KEY-----)\1') {
    $keyVal = $matches[2].Trim()
    if ($keyVal) {
        Write-Host "Setting DEPLOY_SSH_KEY from .env..." -NoNewline
        $keyVal | gh secret set DEPLOY_SSH_KEY @envArgs
        Write-Host " [DONE]" -ForegroundColor Green
    }
}

$content = Get-Content $envPath
foreach ($line in $content) {
    if ($line -match '^\s*DEPLOY_SSH_HOST=(.+)$') {
        $val = $matches[1].Trim('"' + "'" + ' ')
        if ($val) {
            Write-Host "Setting DEPLOY_SSH_HOST..." -NoNewline
            $val | gh secret set DEPLOY_SSH_HOST @envArgs
            Write-Host " [DONE]" -ForegroundColor Green
        }
    }
    elseif ($line -match '^\s*DEPLOY_SSH_USER=(.+)$') {
        $val = $matches[1].Trim('"' + "'" + ' ')
        if ($val) {
            Write-Host "Setting DEPLOY_SSH_USER..." -NoNewline
            $val | gh secret set DEPLOY_SSH_USER @envArgs
            Write-Host " [DONE]" -ForegroundColor Green
        }
    }
    elseif ($line -match '^\s*DEPLOY_SSH_PORT=(.+)$') {
        $val = $matches[1].Trim('"' + "'" + ' ')
        if ($val) {
            Write-Host "Setting DEPLOY_SSH_PORT..." -NoNewline
            $val | gh secret set DEPLOY_SSH_PORT @envArgs
            Write-Host " [DONE]" -ForegroundColor Green
        }
    }
}

Write-Host "`nAll secrets from $envPath successfully pushed to GitHub!" -ForegroundColor Green
