# IoT InfraLab — Documentation Index

Complete reference for IoT cybersecurity simulation lab (Final Year Project).

## Architecture & Design

| File | Description |
|------|-------------|
| [01-architecture-overview.md](01-architecture-overview.md) | System architecture, 4-zone topology, network layout |
| [14-network-topology.md](14-network-topology.md) | Subnet design, IP assignments, bridge config |
| [20-technical-decisions.md](20-technical-decisions.md) | Key decisions table with alternatives and rationale |

## Core Infrastructure

| File | Description |
|------|-------------|
| [02-mqtt-broker.md](02-mqtt-broker.md) | Mosquitto — config, vulnerability rationale, ACL |
| [03-nodered-automation.md](03-nodered-automation.md) | Node-RED — flows, dashboard, sensor lifecycle |
| [04-docker-proxy.md](04-docker-proxy.md) | Docker socket proxy — API security boundary |

## Simulation

| File | Description |
|------|-------------|
| [05-sensor-simulation.md](05-sensor-simulation.md) | docker_sensor — profiles, telemetry, OTEL spans |
| [06-attack-simulation.md](06-attack-simulation.md) | docker_attacker — killchain, tools, scripts |
| [07-security-auditor.md](07-security-auditor.md) | security-auditor — nmap + Gemini AI pipeline |

## Security

| File | Description |
|------|-------------|
| [08-suricata-ids-ips.md](08-suricata-ids-ips.md) | Suricata — rules, modes, MQTT inspection |
| [15-security-model.md](15-security-model.md) | Intentional vulnerabilities, hardening guide |

## Observability

| File | Description |
|------|-------------|
| [09-observability-stack.md](09-observability-stack.md) | LGTM stack, OTEL collector, Promtail pipeline |
| [10-grafana-dashboards.md](10-grafana-dashboards.md) | All 3 dashboards — panels, queries, data sources |
| [11-telegraf-metrics.md](11-telegraf-metrics.md) | Telegraf — host + container monitoring |
| [12-influxdb-schema.md](12-influxdb-schema.md) | Buckets, measurements, tags, field design |
| [13-distributed-tracing.md](13-distributed-tracing.md) | OTEL spans → collector → Tempo → Grafana |

## Configuration & Tooling

| File | Description |
|------|-------------|
| [16-configuration-files.md](16-configuration-files.md) | Config reference: .env, sensor blueprints |
| [17-dashboard-generator.md](17-dashboard-generator.md) | gen_dashboards.py — programmatic JSON generation |

## Operations

| File | Description |
|------|-------------|
| [18-testing-verification.md](18-testing-verification.md) | Smoke tests, manual verification steps |
| [19-deployment-guide.md](19-deployment-guide.md) | Prerequisites, quick start, troubleshooting |

---

**Project repo root:** [../README.md](../README.md)
**Assets:** `assets/` — diagrams, screenshots, topology images
