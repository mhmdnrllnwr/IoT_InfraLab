# Observability Stack (LGTM)

## Purpose

Complete Grafana LGTM observability stack for logs, metrics, traces, and dashboards. Provides full visibility into telemetry pipeline, platform health, and security events.

## Components

### Loki — Log Aggregation

**Image:** `grafana/loki:latest`
**Container:** `loki`
**User:** `root`
**Port:** 3100
**Memory:** 384 MB limit / 192 MB reserved

**Configuration:** `infrastructure/loki/local-config.yaml`

| Setting | Value | Purpose |
|---------|-------|---------|
| Mode | Single-instance (`-target=all`) | Lab deployment |
| Storage | Filesystem (`/tmp/loki`) | Named volume `loki_data` |
| Schema | TSDB v13 (from 2024-01-01) | Current stable index format |
| Retention | 168h (7 days) | Bound disk usage |
| Ingestion limit | 10 MB/s | Prevent overload |
| Max streams/user | 1000 | Limit cardinality |
| Max entries/query | 5000 | Query performance |
| Query cache | 50 MB embedded | Faster repeated queries |
| Chunk idle | 15m | Flush inactive chunks |
| Chunk max age | 1h | Force flush interval |
| Chunk target size | 512 KB | Chunk granularity |
| Log level | warn | Reduce noise |

### Promtail — Log Shipper

**Image:** `grafana/promtail:latest`
**Container:** `promtail`
**IP:** `172.18.0.10` (static)
**Memory:** 64 MB

**Configuration:** `infrastructure/promtail/promtail-config.yaml`

**Source:** `/var/log/suricata/eve.json` (from named volume `suricata_logs`)

**Pipeline:**
1. Read JSON lines from eve.json
2. Extract fields: `timestamp`, `event_type`, `src_ip`, `dest_ip`, `alert`
3. Apply 50% sampling to non-alert events (reduce volume)
4. Extract labels: `event_type`, `src_ip`
5. Drop `filename` and `stream` labels (reduce cardinality)

**Shipping:** `http://loki:3100/loki/api/v1/push`
- Batch wait: 5s
- Batch size: 512 KB
- Retries: 3
- Rate limit: 1000 lines/s read, 2000 burst

### Tempo — Distributed Tracing

**Image:** `grafana/tempo:latest`
**Container:** `tempo`
**Ports:** 4317 (gRPC), 4318 (HTTP) — internal
**Memory:** 256 MB limit / 128 MB reserved

**Configuration:** `infrastructure/tempo/tempo-config.yaml`

- OTLP receiver on gRPC 4317 and HTTP 4318
- Local storage backend at `/tmp/tempo/blocks`
- WAL at `/tmp/tempo/wal`
- Log level: warn

### OTEL Collector — Trace Pipeline

**Image:** `otel/opentelemetry-collector:latest`
**Container:** `otel_collector`
**Ports:** 4317 (gRPC), 4318 (HTTP)
**Memory:** 128 MB

**Configuration:** `infrastructure/otel/otel-config.yaml`

```
Receivers: [otlp]
  → Processors: [batch] (timeout: 5s, batch size: 10)
    → Exporters:
      → otlp/tempo (forward to tempo:4317, insecure)
      → debug (detailed logging)
Pipeline: traces only
```

## Data Flow

### Traces
```
Sensor Node (OTEL span) → OTLP gRPC → OTEL Collector (4317)
  → batch processor → otlp/tempo → Tempo
    → Grafana Explore (Tempo datasource)
```

### Logs
```
Suricata eve.json → Promtail (reads named volume)
  → JSON parse → label extract → Loki (3100)
    → Grafana SOC Dashboard (Loki datasource)
```

### Metrics
```
Sensor MQTT publish → Node-RED → InfluxDB (sensor_data)
Telegraf → Docker API → InfluxDB (platform_metrics)
  → Grafana Dashboards (InfluxDB datasource)
```

## Grafana Data Sources (auto-provisioned)

| Name | Type | URL | UID |
|------|------|-----|-----|
| Loki | Loki | `http://loki:3100` | `Loki` |
| Tempo | Tempo | `http://tempo:3200` | `Tempo` |
| InfluxDB | InfluxDB | `http://influxdb:8086` | `InfluxDB` |

## Related

- Dashboards: [10-grafana-dashboards.md](10-grafana-dashboards.md)
- Trace details: [13-distributed-tracing.md](13-distributed-tracing.md)
- Suricata alert pipeline: [08-suricata-ids-ips.md](08-suricata-ids-ips.md)
