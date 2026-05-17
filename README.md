# IoT InfraLab

IoT cybersecurity simulation lab for Final Year Project. Docker Compose-orchestrated network with MQTT telemetry, Node-RED automation, Suricata IDS/IPS, OpenTelemetry distributed tracing, and Grafana LGTM observability stack. Supports dynamic sensor simulation, AI-powered vulnerability scanning, and cyber attack killchain scenarios.

## Architecture

```
Trusted Zone (Core Infra)    Management Zone      Analytics Zone              Intrusion Detection
┌──────────────────────┐   ┌────────────────┐   ┌──────────────────────┐    ┌──────────────────────┐
│ mosquitto (MQTT)     │   │ docker-proxy   │   │ influxdb (time-series)│    │ suricata (IDS/IPS)   │
│   :1883              │   │ (socket proxy) │   │ grafana :3000         │    │   (mosquitto net ns) │
│ nodered (Node-RED)   │   │   :2375(int)   │   │ loki :3100            │    │ security-auditor     │
│   :1880              │   └────────────────┘   │ tempo (traces)        │    │   :172.18.0.100      │
│   :172.18.0.25       │                       │ otel-collector :4317  │    └──────────────────────┘
└──────────────────────┘                       │ telegraf (metrics)    │
                                                │ promtail :172.18.0.10 │
                                                └──────────────────────┘
```

**Network:** `iot_infralab_net` — bridge, subnet `172.18.0.0/24`, interface `br-iotlab`

## Services

| # | Service | Container | Port(s) | Purpose |
|---|---------|-----------|---------|---------|
| 1 | mosquitto | iot_broker | 1883, 9001 | MQTT message broker |
| 2 | nodered | iot_nodered | 1880 | Node-RED flow automation + Dashboard 2.0 UI |
| 3 | docker-proxy | docker_api_proxy | (internal) | Secure Docker API proxy for container mgmt |
| 4 | influxdb | influxdb | 8086 | Time-series database for IoT sensor data |
| 5 | telegraf | telegraf | (internal) | Host and container metrics collection |
| 6 | grafana | grafana | 3000 | Dashboards: IoT sensors, platform health, SOC |
| 7 | loki | loki | 3100 | Log aggregation for Suricata alerts |
| 8 | tempo | tempo | (internal) | Distributed tracing backend (OTLP) |
| 9 | otel-collector | otel_collector | 4317, 4318 | OpenTelemetry collector pipeline |
| 10 | promtail | promtail | (internal) | Log shipper: Suricata eve.json → Loki |
| 11 | suricata | suricata-ids | (net mode) | IDS/IPS with MQTT app-layer parsing |
| 12 | security-auditor | security_auditor | (internal) | AI-powered vulnerability scanner (Gemini) |

## Prerequisites

- Docker Desktop 4.30+ with WSL2 backend
- WSL2 (Ubuntu 22.04 recommended)
- Minimum 8GB RAM allocated to Docker
- Git
- Gemini API key (for security auditor — optional, skip to run without)

## Quick Start

```powershell
# 1. Clone
git clone <repo-url> IoT_InfraLab
cd IoT_InfraLab

# 2. Environment setup
# Edit .env with your GEMINI_API_KEY (or leave blank — auditor runs in degraded mode)
# INFLUXDB_TOKEN is auto-generated for first run

# 3. Start stack
docker compose up -d

# 4. Verify all services running
docker compose ps

# 5. Access UIs
# Node-RED Dashboard: http://localhost:1880/dashboard
# Grafana:            http://localhost:3000  (admin123 / admin123)
# Node-RED Editor:    http://localhost:1880
```

## Usage Scenarios

### 1. Sensor Management

Node-RED **Node Management** tab provides full lifecycle control for simulated IoT sensors:

1. **Define sensor types** — temperature, humidity, pressure, vibration, power consumption
2. **Configure sensor** — assign ID, type(s), behavior profile (normal/failing/erratic), publish interval
3. **Deploy** — Node-RED creates a Docker container running `simulator.py`
4. **Monitor** — live MQTT feed shows telemetry in real time
5. **Control** — start, stop, pause, restart, or kill individual sensors

Sensor publishes JSON telemetry to `sensors/factory/{sensor_id}` at configured interval.

**Behavior profiles:**
- **Normal:** Random values within configured range
- **Failing:** Gradual drift upward (5% every 30 seconds)
- **Erratic:** 10% chance of extreme spikes (2x–4x baseline)

### 2. Attack Simulation

**Cyber Attack Simulation** tab automates a 5-stage killchain:

| Stage | Action | Tool |
|-------|--------|------|
| 0. Create Attacker | Deploy attacker container | Docker API |
| 1. Breach Network | Connect attacker to iot_infralab_net | Docker network |
| 2. Reconnaissance | Nmap scan of 172.18.0.0/24 | Nmap |
| 3. Sniff MQTT | Subscribe to all topics (#) | mqtt_sniff.py |
| 4. Impact | SYN flood against MQTT broker (1883) | Hping3 |
| 5. Remove Traces | Delete attacker container | Docker API |

**Standalone attack tools** (exec inside attacker container):
- `python mqtt_inject.py` — inject fake MQTT telemetry
- `python mqtt_sniff.py` — subscribe and dump all MQTT traffic
- `python mqtt_dos.py` — multi-threaded application-layer DoS

### 3. SOC Monitoring

**Security Ops** tab provides:

- **Network topology** — live container map via Docker API polling
- **Suricata alerts** — real-time IDS/IPS alert stream from eve.json
- **NAC** — isolate suspicious containers from iot_infralab_net
- **AI security audit** — trigger nmap scan + Gemini AI analysis of exposed ports
- **IPS mode toggle** — switch Suricata between alert (IDS) and drop (IPS) rules

**Grafana dashboards:**
| Dashboard | Source | Key Panels |
|-----------|--------|------------|
| IoT Sensors Overview | InfluxDB | Temperature, vibration, power trend; anomaly detection |
| Platform Health | InfluxDB | Host CPU/mem/network, per-container metrics, service status |
| Security Operations (SOC) | Loki | Alert timeline, severity breakdown, top attacker IPs, logs |

### 4. Distributed Tracing

Full trace chain across services:

```
Sensor node → MQTT publish (OTEL span) → Mosquitto → Security Auditor trigger (OTEL span)
  → Nmap scan (sub-span) → Gemini AI analysis (sub-span) → Report publish (sub-span)
```

View traces in Grafana: **Explore → Tempo** — query `{service.name="security-auditor"}` or `{service.name="iot-sensor-node-*"}`

## Security Model

This lab intentionally uses insecure configurations for educational attack/defense scenarios.

| Risk | Location | Rationale |
|------|----------|-----------|
| Anonymous MQTT | mosquitto:1883 | Enables MQTT sniffing, injection, and DoS attack scenarios |
| Docker API POST/DELETE/EXEC | docker-proxy | Enables Node-RED container lifecycle management + kill switch |
| Grafana weak credentials | .env (admin123/admin123) | Demo simplicity; change for any production-adjacent use |
| Plaintext protocols | All services | TLS would prevent Suricata from inspecting MQTT payloads |

**Hardening available:** Switch Mosquitto to `mosquitto_hardened.conf` (password + ACL enforced). Files exist at `infrastructure/mosquitto/config/`. Requires updating Node-RED MQTT broker credentials and rebuilding flow credentials.

## Project Structure

```
IoT_InfraLab/
├── config/                          # Sensor blueprints and type definitions
│   ├── sensor_settings.json         # Blueprint definitions (5 sensor types)
│   └── sensor_types.json            # Base ranges for random value generation
├── infrastructure/                  # Per-service configs
│   ├── suricata/                    # IDS/IPS rules and config
│   │   ├── local.rules.ids         # Alert mode rules
│   │   ├── local.rules.ips         # Drop mode rules
│   │   └── local.rules.vuln        # Pass-only rules
│   ├── grafana/provisioning/        # Auto-provisioned datasources + dashboards
│   ├── influxdb/config/             # InfluxDB connection configs
│   ├── mosquitto/config/            # MQTT broker configs (vulnerable + hardened)
│   ├── loki/                        # Log aggregation config
│   ├── tempo/                       # Tracing config
│   ├── otel/                        # OpenTelemetry collector pipeline
│   ├── promtail/                    # Log shipper config
│   └── telegraf/                    # Metrics collection config
├── src/simulation/                  # Simulation containers
│   ├── docker_sensor/              # IoT sensor simulator (Python + OTEL)
│   ├── auditor_security/           # AI security auditor (Gemini + nmap + OTEL)
│   ├── docker_attacker/            # Attack tools (sniff, inject, DoS)
│   └── nodered/NodeRed_Data/       # Node-RED flows, settings, configs
├── test/
│   └── smoke_test.py               # Integration smoke test
├── text/                            # Planning docs and flow exports
├── gen_dashboards.py                # Grafana dashboard generator
└── docker-compose.yaml              # 12-service stack definition
```

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Container exits immediately | Memory limit too low | `docker compose logs <service>`; increase limits in compose |
| Suricata no alerts | Wrong network mode | Suricata shares mosquitto's network — verify `network_mode: service:mosquitto` |
| Gemini AI returns errors | Missing API key or quota | Check `GEMINI_API_KEY` in `.env`; verify billing in Google AI Studio |
| Sensor containers can't start | Docker socket proxy not ready | `docker compose restart docker-proxy` |
| Blank Grafana dashboards | No data in InfluxDB/Loki | Deploy sensors via Node-RED; run attack simulation to generate Suricata alerts |
| OTEL traces not visible | Collector not receiving | `docker compose logs otel-collector`; check `http://otel-collector:4317` reachability |
| Named volume data loss | Using `docker compose down -v` | Use `docker compose down` without `-v` to preserve volumes |

## Verification

```powershell
# Smoke test (all services must be running)
python test/smoke_test.py

# Expected output:
# [1/5] MQTT Broker ......... OK
# [2/5] InfluxDB ............ OK
# [3/5] Grafana ............. OK
# [4/5] Node-RED ............ OK
# [5/5] Data Pipeline ....... OK
```

## FYP Context

This project demonstrates:
- **IoT telemetry pipeline** — sensor → MQTT → InfluxDB → Grafana
- **OpenTelemetry distributed tracing** — sensor → OTEL collector → Tempo → Grafana
- **AI-powered security analysis** — nmap + Gemini API vulnerability assessment
- **Real-time intrusion detection** — Suricata IDS/IPS with MQTT app-layer parsing
- **Dynamic container orchestration** — Node-RED + Docker socket proxy
- **Log aggregation and alert correlation** — Suricata → Promtail → Loki → Grafana SOC dashboard
- **Cyber attack killchain** — automated multi-stage attack scenarios with full observability

### Key Technical Decisions

- **Mosquitto anonymous by default:** Enables realistic attack scenarios where adversary can sniff/inject without credentials
- **Docker socket proxy (not direct mount):** Security boundary between Node-RED and Docker daemon; allows fine-grained API permission control
- **OTEL collector as intermediary:** Decouples trace producers (sensors, auditor) from trace storage (Tempo); enables pipeline transformation without client changes
- **Named Docker volumes:** Data persists across restarts; survives `docker compose down` (without `-v`)
- **YAML-based provisioning:** Grafana dashboards and datasources are declarative — reproducible across environments
