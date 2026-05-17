# Architecture Overview

## Purpose

IoT InfraLab is a Docker Compose-orchestrated cybersecurity simulation lab demonstrating IoT telemetry pipelines, real-time intrusion detection, AI-powered vulnerability analysis, and cyber attack killchain scenarios. Designed for educational security testing in a controlled environment.

## Four-Zone Model

The system is logically divided into four network zones:

```
Trusted Zone (Core Infra)    Management Zone     Analytics Zone          Intrusion Detection
┌──────────────────────┐   ┌────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ mosquitto (MQTT)     │   │ docker-proxy   │  │ influxdb (time-series)│  │ suricata (IDS/IPS)   │
│   :1883              │   │ (socket proxy) │  │ grafana :3000         │  │   (mosquitto net ns) │
│ nodered (Node-RED)   │   │   :2375(int)   │  │ loki :3100            │  │ security-auditor     │
│   :1880              │   └────────────────┘  │ tempo (traces)        │  │   :172.18.0.100      │
│   :172.18.0.25       │                       │ otel-collector :4317  │  └──────────────────────┘
└──────────────────────┘                       │ telegraf (metrics)    │
                                                │ promtail :172.18.0.10 │
                                                └──────────────────────┘
```

### Trusted Zone
Core infrastructure services: MQTT message broker and Node-RED automation engine. These are the primary services that all other components interact with.

### Management Zone
Docker socket proxy — a security boundary between Node-RED and the Docker daemon. Enables fine-grained API permission control without exposing the full Docker socket.

### Analytics Zone
Complete Grafana LGTM observability stack: InfluxDB for time-series sensor data, Loki for log aggregation, Tempo for distributed tracing, OTEL collector for trace ingestion, Telegraf for host/container metrics, Promtail for log shipping.

### Intrusion Detection Zone
Suricata IDS/IPS (shares Mosquitto's network namespace for full traffic visibility) and the security auditor container (AI-powered vulnerability scanning).

## Service Dependency Graph

```
mosquitto ──┬── nodered ──┬── docker-proxy
            │              │
            │              └── influxdb ──┬── grafana
            │                             │
            │                             └── telegraf ──┬── docker-proxy
            │                                            │
            ├── suricata                                 └── influxdb
            │
            ├── security-auditor ──┬── mosquitto
            │                      └── otel-collector ──┬── tempo
            │                                           │
            └── promtail ──┬── loki                      └── influxdb
                           └── suricata (logs volume)
```

## Data Flows

### Sensor Telemetry Path
```
Sensor Container → MQTT Publish (sensors/factory/{id})
  → Mosquitto Broker → Node-RED Subscribe
    → InfluxDB Out Node → InfluxDB (sensor_data bucket)
      → Grafana Dashboard Queries
```

### Trace Path
```
Sensor/Auditor → OTLP gRPC → OTEL Collector → Tempo → Grafana Explore
```

### Log Path
```
Suricata eve.json → Promtail → Loki → Grafana SOC Dashboard
```

## IP Address Assignments

| Service | IP Address | Assignment |
|---------|-----------|------------|
| Node-RED | 172.18.0.25 | Static |
| Promtail | 172.18.0.10 | Static |
| Security Auditor | 172.18.0.100 | Static |
| Mosquitto | DHCP | Dynamic |
| Loki | DHCP | Dynamic |
| Tempo | DHCP | Dynamic |
| InfluxDB | DHCP | Dynamic |
| Telegraf | DHCP | Dynamic |
| Grafana | DHCP | Dynamic |
| OTEL Collector | DHCP | Dynamic |
| Docker Proxy | DHCP | Dynamic |
| Suricata | (shares mosquitto netns) | None |

## Resource Limits Summary

| Service | Memory Limit | Memory Reservation |
|---------|-------------|-------------------|
| InfluxDB | 512 MB | 256 MB |
| Node-RED | 384 MB | 256 MB |
| Loki | 384 MB | 192 MB |
| Grafana | 384 MB | 192 MB |
| Tempo | 256 MB | 128 MB |
| Suricata | 256 MB | — |
| Security Auditor | 128 MB | — |
| OTEL Collector | 128 MB | — |
| Telegraf | 80 MB | — |
| Mosquitto | 64 MB | — |
| Promtail | 64 MB | — |
| Docker Proxy | 32 MB | — |

## Key Design Principles

1. **Security through observability** — every component is monitored; attacks produce visible alerts in dashboards
2. **Defense in depth** — Suricata IDS/IPS + SOC monitoring + AI auditor + container isolation
3. **Educational transparency** — protocols are intentionally plaintext for inspection
4. **Dynamic orchestration** — Node-RED manages container lifecycle via Docker API proxy
5. **Reproducible deployment** — single `docker compose up` provisions the full stack
