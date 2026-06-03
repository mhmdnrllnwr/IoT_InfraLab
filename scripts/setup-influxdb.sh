#!/usr/bin/env bash
# InfluxDB initialization for IoT InfraLab.
# Idempotent: creates org + all 4 buckets only if missing.
# Usage: bash scripts/setup-influxdb.sh
set -euo pipefail

BUCKETS=("sensor_data" "sensor_saved" "sensor_metadata" "platform_metrics")

echo "Waiting for InfluxDB to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8086/health > /dev/null 2>&1; then
    echo "InfluxDB ready."
    break
  fi
  sleep 2
done

# Source .env for token
if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env first."
  exit 1
fi
export "$(grep -E '^INFLUXDB_TOKEN=' .env | head -1)"

if [ -z "${INFLUXDB_TOKEN:-}" ]; then
  echo "ERROR: INFLUXDB_TOKEN not found in .env"
  exit 1
fi

# Get existing buckets
EXISTING_BUCKETS=$(docker compose exec influxdb influx bucket list -o infralab --token="$INFLUXDB_TOKEN" 2>/dev/null || echo "")

# Run initial setup if org doesn't exist yet
if ! echo "$EXISTING_BUCKETS" | grep -q "infralab"; then
  echo "Running initial InfluxDB setup..."
  docker compose exec influxdb influx setup \
    --org infralab \
    --bucket sensor_data \
    --username admin123 \
    --password admin123 \
    --token "$INFLUXDB_TOKEN" \
    --force 2>&1
  echo "Initial setup complete."
else
  echo "InfluxDB already set up."
fi

# Create any missing buckets
for bucket in "${BUCKETS[@]}"; do
  if echo "$EXISTING_BUCKETS" | grep -q "$bucket"; then
    echo "Bucket '$bucket' exists. Skip."
  else
    echo "Creating bucket '$bucket'..."
    docker compose exec influxdb influx bucket create \
      --org infralab \
      --name "$bucket" \
      --token "$INFLUXDB_TOKEN" 2>&1
  fi
done

echo ""
echo "SUCCESS: All buckets ready."
echo "  - sensor_data"
echo "  - sensor_saved"
echo "  - sensor_metadata"
echo "  - platform_metrics"
