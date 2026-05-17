# IoT InfraLab Setup Script (Windows PowerShell)
# Run: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== IoT InfraLab Setup ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check prerequisites
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

$dockerVersion = docker --version 2>$null
if (-not $dockerVersion) {
    Write-Host "ERROR: Docker not found. Install Docker Desktop from https://docs.docker.com/desktop/" -ForegroundColor Red
    exit 1
}
Write-Host "  OK: $dockerVersion"

$composeVersion = docker compose version 2>$null
if (-not $composeVersion) {
    Write-Host "ERROR: docker compose not available. Update Docker Desktop to 4.30+." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: $composeVersion"

# 2. Create .env from template
Write-Host "[2/5] Setting up .env..." -ForegroundColor Yellow
Push-Location $projectRoot
$envFile = Join-Path $projectRoot ".env"
$envExample = Join-Path $projectRoot ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  Created .env from .env.example"
        Write-Host "  WARNING: Edit .env with your GEMINI_API_KEY and secrets!" -ForegroundColor Red
    } else {
        Write-Host "  WARNING: .env.example not found. Create .env manually." -ForegroundColor Red
    }
} else {
    Write-Host "  .env already exists, skipping."
}

# 3. Create required directories
Write-Host "[3/5] Creating required directories..." -ForegroundColor Yellow
$dirs = @(
    "infrastructure/mosquitto/data",
    "infrastructure/mosquitto/log",
    "infrastructure/suricata/run",
    "infrastructure/suricata/logs",
    "infrastructure/influxdb/data",
    "infrastructure/influxdb/config",
    "infrastructure/grafana/data",
    "infrastructure/loki/data"
)
foreach ($d in $dirs) {
    $fullPath = Join-Path $projectRoot $d
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Force -Path $fullPath | Out-Null
        Write-Host "  Created: $d"
    }
}
Write-Host "  Done."

# 4. Validate docker compose config
Write-Host "[4/5] Validating docker compose config..." -ForegroundColor Yellow
try {
    docker compose config > $null
    Write-Host "  OK: docker-compose.yaml is valid."
} catch {
    Write-Host "  ERROR: docker compose config failed. Check docker-compose.yaml." -ForegroundColor Red
    exit 1
}

# 5. Next steps
Write-Host "[5/5] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env file with your secrets"
Write-Host "     notepad .env"
Write-Host ""
Write-Host "  2. Build custom images"
Write-Host "     docker compose build security-auditor"
Write-Host ""
Write-Host "  3. Start the stack"
Write-Host "     docker compose up -d"
Write-Host ""
Write-Host "  4. Access services"
Write-Host "     Node-RED:  http://localhost:1880"
Write-Host "     Grafana:   http://localhost:3000   (admin / your_password)"
Write-Host "     InfluxDB:  http://localhost:8086"
Write-Host ""
Write-Host "  5. Generate Grafana dashboards (if needed)"
Write-Host "     python gen_dashboards.py"

Pop-Location
