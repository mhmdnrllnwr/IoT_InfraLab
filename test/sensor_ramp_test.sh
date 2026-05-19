#!/bin/bash
# Sensor Container Ramp Test
# Creates sensor containers in batches, monitors resources, stops at limit.
# Usage: bash src/simulation/sensor_ramp_test.sh [batch_size] [max_batches]
#
# Default: batch_size=10, max_batches=10 (up to 100 sensors)

BATCH_SIZE=${1:-10}
MAX_BATCHES=${2:-10}
IMAGE="general-iot-sensor:latest"
NETWORK="iot_infralab_net"
PREFIX="sensor_test"
TOTAL=0
BATCH=1

cleanup() {
    echo "[CLEANUP] Removing all test containers..."
    docker ps -a --filter "name=${PREFIX}" -q | xargs -r docker rm -f
    echo "[CLEANUP] Done."
}

# Cleanup on exit
trap cleanup EXIT

echo "=== Sensor Ramp Test ==="
echo "Image:    $IMAGE"
echo "Network:  $NETWORK"
echo "Batch:    $BATCH_SIZE containers per batch"
echo "Max:      $((BATCH_SIZE * MAX_BATCHES)) total"
echo ""

# Verify infra is healthy
docker info > /dev/null 2>&1 || { echo "Docker not running"; exit 1; }
docker network inspect "$NETWORK" > /dev/null 2>&1 || { echo "Network $NETWORK not found"; exit 1; }

while [ $BATCH -le $MAX_BATCHES ]; do
    START=$((TOTAL + 1))
    END=$((TOTAL + BATCH_SIZE))

    echo "[BATCH $BATCH] Creating sensors $START-$END..."

    for i in $(seq $START $END); do
        NAME="${PREFIX}_$(printf '%03d' $i)"
        docker run -d \
            --network "$NETWORK" \
            --memory="64m" \
            --memory-reservation="32m" \
            --name "$NAME" \
            -e SENSOR_ID="$NAME" \
            -e SENSOR_TYPES="DHT11" \
            -e INTERVAL=5 \
            --restart no \
            "$IMAGE" > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "[FAIL] Container $NAME creation failed. Limit reached."
            docker ps -a --filter "name=${PREFIX}" -q | wc -l
            exit 1
        fi
        # Small stagger to avoid thundering herd on MQTT broker
        sleep 0.1
    done

    TOTAL=$END

    # Check Docker daemon health
    docker info > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[FAIL] Docker daemon unhealthy at $TOTAL containers."
        exit 1
    fi

    # Resource summary
    echo "[BATCH $BATCH] Sensors: $TOTAL"
    echo "--- Container Memory ---"
    docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' 2>/dev/null | grep "$PREFIX" \
        | awk 'BEGIN{s=0;c=0} {gsub(/MiB/,"",$3); s+=$3; c++} END{printf "Total: %.0f MiB  Avg: %.0f MiB\n", s, s/c}'

    echo "--- Critical Services ---"
    docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null \
        | grep -E 'influxdb|iot_broker|grafana'

    # Check MQTT health
    SAMPLE=$(docker exec iot_broker mosquitto_sub -t "sensors/factory/+" -C 3 -W 3 2>&1 | wc -l)
    echo "--- MQTT messages in 3s: $SAMPLE ---"
    echo ""

    BATCH=$((BATCH + 1))
done

echo "=== Test complete: $TOTAL sensors created ==="
