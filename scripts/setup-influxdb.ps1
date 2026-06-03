<#
.SYNOPSIS
    InfluxDB initialization for IoT InfraLab.
.DESCRIPTION
    Creates org + all 4 buckets (sensor_data, sensor_saved, sensor_metadata,
    platform_metrics) idempotently. Safe to re-run.
.EXAMPLE
    .\scripts\setup-influxdb.ps1
#>

$ErrorActionPreference = "Stop"
$buckets = @("sensor_data", "sensor_saved", "sensor_metadata", "platform_metrics")

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
    Write-Host "ERROR: INFLUXDB_TOKEN not found in .env" - ForegroundColor Red
    exit 1
}
$token = $tokenLine.Line -replace '^INFLUXDB_TOKEN=', ''
$token = $token.Trim()

# Validate token format (64-char hex for openssl rand -hex 32)
if ($token -notmatch '^[a-f0-9]{64}$') {
    Write-Host "WARNING: INFLUXDB_TOKEN does not look like a valid 64-char hex string." -ForegroundColor Yellow
    Write-Host "  Expected format: 64 hex characters (openssl rand -hex 32)" -ForegroundColor Yellow
    Write-Host "  Got: $($token.Substring(0, [Math]::Min($token.Length, 20)))..." -ForegroundColor Yellow
    Write-Host "  Check .env for trailing characters (e.g. '>' from copy-paste)." -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') { exit 1 }
}

# Get existing buckets
$existingBuckets = docker compose exec influxdb influx bucket list -o infralab --token $token 2>&1

# Run initial setup if org doesn't exist
if ($LASTEXITCODE -ne 0) {
    Write-Host "Running initial InfluxDB setup..." -ForegroundColor Yellow
    docker compose exec influxdb influx setup `
        --org infralab `
        --bucket sensor_data `
        --username admin123 `
        --password admin123 `
        --token $token `
        --force 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: influx setup failed." -ForegroundColor Red
        Write-Host "Clear volume and retry: docker compose down -v influxdb" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Initial setup complete." -ForegroundColor Green
} else {
    Write-Host "InfluxDB already set up." -ForegroundColor Green
}

# Refresh bucket list after potential setup
$existingBuckets = docker compose exec influxdb influx bucket list -o infralab --token $token 2>&1

# Create any missing buckets
foreach ($bucket in $buckets) {
    if ($existingBuckets -match $bucket) {
        Write-Host "Bucket '$bucket' exists. Skip." -ForegroundColor Cyan
    } else {
        Write-Host "Creating bucket '$bucket'..." -ForegroundColor Yellow
        docker compose exec influxdb influx bucket create `
            --org infralab `
            --name $bucket `
            --token $token 2>&1
    }
}

Write-Host "" -ForegroundColor Green
Write-Host "SUCCESS: All buckets ready." -ForegroundColor Green
Write-Host "  - sensor_data" -ForegroundColor Cyan
Write-Host "  - sensor_saved" -ForegroundColor Cyan
Write-Host "  - sensor_metadata" -ForegroundColor Cyan
Write-Host "  - platform_metrics" -ForegroundColor Cyan
