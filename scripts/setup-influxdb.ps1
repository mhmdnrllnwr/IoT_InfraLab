<#
.SYNOPSIS
    One-time InfluxDB initialization for fresh IoT InfraLab setups.
.DESCRIPTION
    Runs `influx setup` to create org, bucket, and admin token.
    Only needed when the influxdb_data named volume is empty (first run
    after `docker compose down -v` or fresh clone).
    On subsequent restarts, the bolt file persists in the named volume
    and InfluxDB starts normally without re-init.
.EXAMPLE
    .\scripts\setup-influxdb.ps1
#>

$ErrorActionPreference = "Stop"

# Wait for InfluxDB to be ready
Write-Host "Waiting for InfluxDB to be ready..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8086/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Host "ERROR: InfluxDB not reachable on localhost:8086" -ForegroundColor Red
    Write-Host "Ensure stack is running: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "InfluxDB ready." -ForegroundColor Green

# Extract token from .env
$envFile = Join-Path $PSScriptRoot ".." ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env not found at $envFile" -ForegroundColor Red
    exit 1
}

$tokenLine = Select-String -Path $envFile -Pattern "^INFLUXDB_TOKEN="
if (-not $tokenLine) {
    Write-Host "ERROR: INFLUXDB_TOKEN not found in .env" -ForegroundColor Red
    exit 1
}
$token = $tokenLine.Line -replace '^INFLUXDB_TOKEN=', ''
$token = $token.Trim()

Write-Host "Running influx setup..." -ForegroundColor Yellow
docker compose exec influxdb influx setup `
    --org infralab `
    --bucket sensor_data `
    --username admin123 `
    --password admin123 `
    --token $token `
    --force 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: InfluxDB initialized." -ForegroundColor Green
    Write-Host "Org: infralab" -ForegroundColor Cyan
    Write-Host "Bucket: sensor_data" -ForegroundColor Cyan
} else {
    Write-Host "ERROR: influx setup failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    Write-Host "If config already exists, this is normal — InfluxDB is already initialized." -ForegroundColor Yellow
}
