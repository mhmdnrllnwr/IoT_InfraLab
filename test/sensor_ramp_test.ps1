# Sensor Container Ramp Test (PowerShell)
# Creates sensor containers in batches, monitors resources, stops at limit.
# Usage: .\src\simulation\sensor_ramp_test.ps1 [-BatchSize 10] [-MaxBatches 10]

param(
    [int]$BatchSize = 10,
    [int]$MaxBatches = 10
)

$Image = "general-iot-sensor:latest"
$Network = "iot_infralab_net"
$Prefix = "sensor_test"
$Total = 0
$Batch = 1

# Trap exit for cleanup
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -SupportEvent -Action {
    Write-Host "[CLEANUP] Removing test containers..."
    docker ps -a --filter "name=$Prefix" -q | ForEach-Object { docker rm -f $_ }
}

Write-Host "=== Sensor Ramp Test ==="
Write-Host "Image:   $Image"
Write-Host "Network: $Network"
Write-Host "Batch:   $BatchSize containers per batch"
Write-Host "Max:     $($BatchSize * $MaxBatches) total"
Write-Host ""

# Verify Docker + network
docker info --format "{{.ServerVersion}}" | Out-Null
if (-not $?) { Write-Host "Docker not running"; exit 1 }

docker network inspect $Network | Out-Null
if (-not $?) { Write-Host "Network $Network not found"; exit 1 }

while ($Batch -le $MaxBatches) {
    $Start = $Total + 1
    $End = $Total + $BatchSize

    Write-Host "[BATCH $Batch] Creating sensors $Start-$End..."

    for ($i = $Start; $i -le $End; $i++) {
        $Name = "${Prefix}_$($i.ToString('000'))"
        docker run -d `
            --network "$Network" `
            --memory="64m" `
            --memory-reservation="32m" `
            --name "$Name" `
            -e SENSOR_ID="$Name" `
            -e SENSOR_TYPES="DHT11" `
            -e INTERVAL=5 `
            --restart no `
            "$Image" *>$null

        if (-not $?) {
            Write-Host "[FAIL] $Name creation failed. Limit reached."
            exit 1
        }
        Start-Sleep -Milliseconds 100
    }

    $Total = $End

    # Check Docker daemon
    docker info --format "{{.ServerVersion}}" | Out-Null
    if (-not $?) {
        Write-Host "[FAIL] Docker daemon unhealthy at $Total containers."
        exit 1
    }

    Write-Host "[BATCH $Batch] Sensors: $Total"

    Write-Host "--- Container Memory ---"
    docker stats --no-stream --format "{{.Name}}\t{{.MemUsage}}" `
        | Select-String "$Prefix" `
        | ForEach-Object {
            $parts = $_ -split "`t"
            $mem = $parts[1]
            # crude sum
        }

    Write-Host "--- Critical Services ---"
    docker stats --no-stream --format "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" `
        | Select-String "influxdb|iot_broker|grafana"

    # Check MQTT
    $mqtt = docker exec iot_broker mosquitto_sub -t "sensors/factory/+" -C 3 -W 3 2>$null
    Write-Host "--- MQTT health: $($mqtt.Count) messages in 3s ---"
    Write-Host ""

    $Batch++
}

Write-Host "=== Test complete: $Total sensors created ==="
