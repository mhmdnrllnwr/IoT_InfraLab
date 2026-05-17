# Telegraf Metrics Collection

## Purpose

Collects host and container performance metrics for the Platform Health dashboard. Runs as a dedicated metrics collector, writing directly to InfluxDB.

## Container

**Image:** `telegraf:latest`
**Container:** `telegraf`
**Memory:** 80 MB
**Collection Interval:** 30s

## Configuration

**File:** `infrastructure/telegraf/telegraf.conf`

### Inputs

| Input | Detail | Tags |
|-------|--------|------|
| `cpu` | Total CPU, `usage_idle` → `100 - usage_idle` | `host` |
| `mem` | Memory used, total, available, etc. | `host` |
| `system` | Load (1m, 5m, 15m), uptime, n_users | `host` |
| `net` | bytes_recv, bytes_sent, packets, errors, drops | `host`, `interface` |
| `docker` | Via `tcp://docker-proxy:2375` — per-container CPU, memory, network | `container_name`, `container_id` |

### Output

```
url: "http://influxdb:8086"
token: "${INFLUXDB_TOKEN}"
organization: "infralab"
bucket: "platform_metrics"
```

### Docker Input Detail

Telegraf connects to `docker-proxy:2375` (NOT the Docker socket directly) — consistent with the project's security model of proxying Docker API access.

Collected per container:
- `docker_container_cpu` — usage_percent
- `docker_container_mem` — usage, limit, usage_percent
- `docker_container_net` — rx_bytes, tx_bytes, rx_packets, tx_packets

## Data Flow

```
Docker daemon → docker-proxy:2375 → Telegraf (docker input)
                                      → InfluxDB (platform_metrics bucket)
                                        → Grafana Platform Health dashboard

Host OS → Telegraf (cpu/mem/system/net inputs)
           → InfluxDB (platform_metrics bucket)
```

## Why Telegraf Over Prometheus

| Factor | Telegraf | Prometheus |
|--------|----------|------------|
| Deployment | Single container | Server + exporters per target |
| InfluxDB output | Native | Requires adapter |
| Docker metrics | Built-in plugin | Requires cadvisor |
| Configuration | Single TOML file | Multiple scrape configs |

Telegraf fits the lab scope — single container, minimal configuration, native InfluxDB output.

## Related

- Platform Health dashboard: [10-grafana-dashboards.md](10-grafana-dashboards.md)
- InfluxDB schema: [12-influxdb-schema.md](12-influxdb-schema.md)
- Docker proxy: [04-docker-proxy.md](04-docker-proxy.md)
