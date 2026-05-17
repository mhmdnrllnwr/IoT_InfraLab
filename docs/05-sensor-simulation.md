# Sensor Simulation (docker_sensor)

## Purpose

Simulates IoT sensor nodes that publish realistic telemetry data to the MQTT broker. Supports multiple behavior profiles for generating normal, failing, and erratic data patterns — enabling anomaly detection testing.

## Container

**Image:** `general-iot-sensor` (built from `src/simulation/docker_sensor/Dockerfile`)
**Base:** `python:3.9-slim`
**Network:** `iot_infralab_net` (DHCP)
**Runtime:** `simulator.py` (150 lines)

### Dependencies

- `paho-mqtt` — MQTT client
- `opentelemetry-api` + `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-grpc` — distributed tracing

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `SENSOR_ID` | Unique identifier (e.g., `CNCMILL-001`) |
| `SENSOR_TYPES` | Comma-separated (e.g., `temperature,vibration`) |
| `NODE_PROFILE` | Behavior profile: `normal`, `failing`, `erratic` |
| `INTERVAL` | Publish interval in seconds |
| `MQTT_BROKER` | Mosquitto hostname (`mosquitto:1883`) |

### Runtime Config Files (mounted from `config/`)

```
config/sensor_types.json  — base value ranges per type
config/sensor_settings.json — blueprint definitions
```

## Sensor Types

| Type | Unit | Range |
|------|------|-------|
| Temperature | °C | 10–40 |
| Humidity | % | 30–90 |
| Pressure | hPa | 950–1050 |
| Vibration | mm/s | 0.0–10.0 |
| Power Consumption | W | 50–500 |

Precision: vibration gets 3 decimal places, all others 1 decimal.

## Behavior Profiles

### Normal
Random uniform value within configured range. Represents healthy sensor operation.

### Failing
Value drifts upward by 5% every 30 seconds (cumulative). Simulates sensor degradation or calibration drift.

### Erratic
10% chance per reading of applying a 2x–4x multiplier spike to the value. Simulates electrical noise or transient faults.

## Data Format

**Topic:** `sensors/factory/{SENSOR_ID}`

```json
{
  "temperature": 28.5,
  "vibration": 0.123,
  "timestamp": "2025-05-14T10:30:00Z"
}
```

## Distributed Tracing

Each MQTT publish is wrapped in an OpenTelemetry span:

```
mqtt_publish_sensors/factory/{SENSOR_ID}
  → OTEL Collector (4317) → Tempo → Grafana
```

Span attributes include:
- `sensor_id`
- `sensor_type`
- `profile`
- `topic`

## Runtime Control

- **Config reload:** subscribes to `cmd/system/reload` — re-reads config files live without restart
- **Lifecycle:** managed by Node-RED via Docker API (create, start, stop, kill)

## Related

- Sensor profiles and blueprints: [16-configuration-files.md](16-configuration-files.md)
- Node-RED sensor management: [03-nodered-automation.md](03-nodered-automation.md)
- Telemetry data in InfluxDB: [12-influxdb-schema.md](12-influxdb-schema.md)
- Traces: [13-distributed-tracing.md](13-distributed-tracing.md)
