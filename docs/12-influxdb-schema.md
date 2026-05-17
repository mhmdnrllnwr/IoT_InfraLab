# InfluxDB Schema

## Purpose

Time-series database storing IoT sensor telemetry and platform performance metrics. Primary data source for Grafana dashboards.

## Container

**Image:** `influxdb:2.7`
**Container:** `influxdb`
**Port:** 8086
**Memory:** 512 MB limit / 256 MB reserved
**Token:** `${INFLUXDB_TOKEN}` from `.env`

### Engine Tuning

```yaml
environment:
  - INFLUXD_ENGINE_CACHE_MAX_MEMORY_SIZE=256MB
  - INFLUXD_ENGINE_CACHE_SNAPSHOT_MEMORY_SIZE=64MB
```

Limits TSM cache to 256 MB and snapshot memory to 64 MB — critical for memory-constrained environment.

### Persistence

Named volume `influxdb_data` mounted at `/var/lib/influxdb2`. Survives `docker compose down` (without `-v`).

## Buckets

### Bucket A: sensor_data

**Purpose:** IoT sensor telemetry from simulated factory sensors.

**Source:** MQTT → Node-RED → InfluxDB Out node

**Measurement: `sensor_data`**

| Element | Type | Values | Source |
|---------|------|--------|--------|
| `value` | Field | float | Sensor reading |
| `sensor_id` | Tag | string | e.g. `CNCMILL-001` |
| `sensor_type` | Tag | string | e.g. `temperature` |
| `profile` | Tag | string | `normal` / `failing` / `erratic` |
| `time` | Timestamp | auto | Millisecond precision |

**Data flow:**
```
Sensor publishes JSON → MQTT → Node-RED subscribe
  → Format Data function (extracts value, tags)
    → InfluxDB Out node → Bucket: sensor_data, Measurement: sensor_data
```

### Bucket B: platform_metrics

**Purpose:** Host and container performance metrics from Telegraf.

**Source:** Telegraf inputs (cpu, mem, system, net, docker)

**Measurements:**

| Measurement | Key Fields | Tags |
|-------------|-----------|------|
| `cpu` | `usage_idle` | `host` |
| `mem` | `used`, `total`, `available`, `used_percent` | `host` |
| `system` | `load1`, `load5`, `load15`, `uptime` | `host` |
| `net` | `bytes_recv`, `bytes_sent`, `packets_recv`, `packets_sent`, `err_in`, `err_out`, `drop_in`, `drop_out` | `host`, `interface` |
| `docker_container_cpu` | `usage_percent` | `host`, `container_name`, `container_id` |
| `docker_container_mem` | `usage`, `limit`, `usage_percent` | `host`, `container_name`, `container_id` |
| `docker_container_net` | `rx_bytes`, `tx_bytes`, `rx_packets`, `tx_packets` | `host`, `container_name`, `container_id` |

### Bucket C: _monitoring (system)

InfluxDB's internal monitoring bucket, created automatically.

## Schema Design Decisions

**Single measurement for all sensor types** — Tags differentiate sensor_id and sensor_type rather than creating separate measurements per type. Simplifies queries and dashboard variable filtering.

**Value as a single field** — Each data point is one value with typed tags. Avoids wide-table schema where each sensor type gets its own column.

**Tags for metadata, fields for values** — `sensor_id`, `sensor_type`, `profile` are indexed tags. Only `value` is a field. This is optimal for InfluxDB performance.

## Query Examples

### Active sensor count (Flux)
```flux
from(bucket: "sensor_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> keep(columns: ["sensor_id"])
  |> distinct(column: "sensor_id")
  |> count()
```

### Average temperature by sensor (Flux)
```flux
from(bucket: "sensor_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r.sensor_type == "temperature")
  |> group(columns: ["sensor_id"])
  |> aggregateWindow(every: 1m, fn: mean)
  |> yield(name: "mean")
```

### Spike detection (Flux)
```flux
from(bucket: "sensor_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r.profile == "erratic" and r.sensor_type == "temperature")
  |> aggregateWindow(every: 1m, fn: count)
```

## Related

- Grafana dashboard queries: [10-grafana-dashboards.md](10-grafana-dashboards.md)
- Telegraf metric source: [11-telegraf-metrics.md](11-telegraf-metrics.md)
- Sensor data format: [05-sensor-simulation.md](05-sensor-simulation.md)
