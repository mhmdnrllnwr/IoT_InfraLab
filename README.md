# IoT InfraLab

IoT cybersecurity simulation lab. Docker Compose orchestrated network with MQTT messaging, Node-RED automation, Suricata intrusion detection, and OpenTelemetry-based observability (LGTM stack: Loki, Grafana, Tempo, Mimir/InfluxDB).

## Architecture

```
Trusted Zone (Core Infra)       Management Zone      Analytics Zone           Intrusion Detection
+------------------------+    +----------------+    +-------------------+    +-------------------+
| mosquitto (MQTT)       |    | docker-proxy   |    | influxdb (2.7)    |    | suricata (IDS)    |
| nodered (Node-RED)     |    | (socket proxy) |    | grafana           |    | security-auditor  |
+------------------------+    +----------------+    | loki / tempo      |    +-------------------+
                                                    | promtail / otel   |
Network: iot_infralab_net (172.18.0.0/24)           +-------------------+
```

- **Trusted Zone**: MQTT broker with intentional vulnerable config for attack simulation. Node-RED manages dynamic sensor/attacker containers via Docker API.
- **Management Zone**: Docker socket proxy securely exposes limited Docker API to Node-RED without full daemon access.
- **Analytics Zone**: InfluxDB for time-series metrics, Grafana for dashboards, Loki for log aggregation, Tempo for distributed tracing, OpenTelemetry Collector for telemetry ingestion.
- **Intrusion Detection**: Suricata monitors network traffic in IDS mode. Security Auditor runs attack simulations.

## Prerequisites

| Requirement | Minimum Version |
|-------------|----------------|
| Docker | 24.0+ |
| Docker Compose | v2 (Docker Desktop 4.30+) |
| Python | 3.9+ (for local scripts) |
| RAM | 4 GB free (stack uses ~2.5 GB) |
| Disk | 2 GB free |

**Docker Desktop (Windows/macOS)**: File sharing must be enabled for the project directory.

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url> IoT_InfraLab
cd IoT_InfraLab

# 2. Run setup script
bash scripts/setup.sh       # Linux/macOS
# or
powershell .\scripts\setup.ps1   # Windows

# 3. Edit .env with your secrets
#    Set GEMINI_API_KEY, generate INFLUXDB_TOKEN, change default passwords

# 4. Build custom images and start
docker compose build security-auditor
docker compose up -d
```

## Detailed Setup

### Step 1: Environment Configuration

Copy `.env.example` to `.env` and fill in:

```ini
# Required: Google Gemini API key (for AI features)
GEMINI_API_KEY=your_key_here

# InfluxDB admin token — generate with: openssl rand -hex 32
INFLUXDB_TOKEN=your_generated_token

# InfluxDB first-run initialization
DOCKER_INFLUXDB_INIT_MODE=setup
DOCKER_INFLUXDB_INIT_USERNAME=admin
DOCKER_INFLUXDB_INIT_PASSWORD=change_this_password
DOCKER_INFLUXDB_INIT_ORG=infralab
DOCKER_INFLUXDB_INIT_BUCKET=sensor_data
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=your_generated_token

# Grafana admin credentials
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=change_this_password

# Node-RED credential encryption secret
NODE_RED_CREDENTIAL_SECRET=change_this_secret

# Host path to project root (for sensor container bind mounts)
# On Linux/macOS: /home/user/IoT_InfraLab
# On Windows: C:/Users/user/IoT_InfraLab
IOT_PROJECT_PATH=.

# Docker network subnet (change if 172.18.0.0/24 conflicts)
IOT_SUBNET=172.18.0.0/24
```

### Step 2: Build and Start

```bash
# Build custom container images
docker compose build security-auditor

# Validate configuration
docker compose config

# Start all services (detached)
docker compose up -d

# Check service health
docker compose ps

# View logs
docker compose logs -f
```

### Step 3: Verify

| Service | URL | Credentials |
|---------|-----|-------------|
| Node-RED | http://localhost:1880 | None (default) |
| Grafana | http://localhost:3000 | admin / your_password |
| InfluxDB | http://localhost:8086 | admin / your_password |

Run the smoke test:
```bash
pip install -r requirements.txt
python test/smoke_test.py
```

## Services

| Service | Container | Port(s) | Image | Purpose |
|---------|-----------|---------|-------|---------|
| Mosquitto | iot_broker | 1883, 9001 | eclipse-mosquitto:2.0 | MQTT broker (vulnerable config) |
| Node-RED | iot_nodered | 1880 | nodered/node-red:4.0 | Flow automation, sensor management |
| Docker Proxy | docker_api_proxy | internal | tecnativa/docker-socket-proxy:0.2 | Secure Docker API access |
| InfluxDB | influxdb | 8086 | influxdb:2.7 | Time-series sensor data |
| Grafana | grafana | 3000 | grafana/grafana-oss:11.1 | Dashboards and alerting |
| Loki | loki | 3100 | grafana/loki:3.1 | Log aggregation |
| Tempo | tempo | internal | grafana/tempo:2.6 | Distributed tracing (OTLP) |
| Promtail | promtail | internal | grafana/promtail:3.1 | Suricata log shipper to Loki |
| OTEL Collector | otel_collector | 4317-4318 | otel/opentelemetry-collector-contrib:0.111 | Telemetry ingestion |
| Suricata | suricata-ids | internal | jasonish/suricata:7.0 | IDS/IPS (network_mode: mosquitto) |
| Security Auditor | security_auditor | internal | (built locally) | Attack simulation |
| Telegraf | telegraf | internal | telegraf:1.32 | Docker host metrics collection |

## Project Structure

```
IoT_InfraLab/
├── config/                  # Sensor blueprints (sensor_settings.json)
├── infrastructure/          # Per-service configs, rules, data mounts
│   ├── suricata/            # Suricata rules (local.rules, *.ids, *.ips, *.vuln)
│   ├── grafana/             # Dashboard provisioning and datasources
│   ├── influxdb/            # InfluxDB config
│   ├── mosquitto/           # MQTT broker configs and credentials
│   ├── otel/                # OpenTelemetry collector pipeline
│   ├── promtail/            # Promtail log shipping config
│   ├── tempo/               # Tempo tracing config
│   ├── telegraf/            # Telegraf metrics config
│   └── loki/                # Loki config
├── src/simulation/          # Simulation containers
│   ├── nodered/             # Node-RED data (flows, settings, nodes)
│   ├── auditor_security/    # Security audit container
│   ├── docker_sensor/       # Sensor simulation container
│   └── docker_attacker/     # Attack container
├── scripts/                 # Setup and utility scripts
├── test/                    # Smoke tests and utilities
├── docker-compose.yaml      # Main service orchestration
├── .env.example             # Environment variable template
└── requirements.txt         # Python dependencies
```

## Common Commands

```bash
# Start / Stop
docker compose up -d                    # Start all services
docker compose down                     # Stop and remove containers
docker compose down -v                  # Also remove volumes (WARNING: data loss)

# Rebuild specific service
docker compose up -d --build security-auditor
docker compose up -d --force-recreate nodered

# View logs
docker compose logs -f suricata         # Follow Suricata logs
docker compose logs --tail=100 loki     # Last 100 Loki lines

# Suricata alerts
docker compose exec suricata cat /var/log/suricata/eve.json | grep '"event_type":"alert"'

# Access containers
docker compose exec nodered bash
docker compose exec influxdb influx setup

# InfluxDB queries (from host)
curl -H "Authorization: Token $INFLUXDB_TOKEN" \
  "http://localhost:8086/api/v2/query?org=infralab" \
  --data-urlencode "q=from(bucket:\"sensor_data\") |> range(start: -10m)"

# Generate Grafana dashboards
python gen_dashboards.py

# Explore metrics
python explore_metrics.py

# List Docker networks
docker network ls | grep iot
```

## Security Model

Mosquitto uses `mosquitto_vulnerable.conf` by default (`allow_anonymous=true`). This is **intentional** — enables MQTT sniffing/injection attack scenarios in the Cyber Attack Simulation tab.

**Do NOT deploy this config in production.**

To harden:
1. Switch to `mosquitto_hardened.conf` in docker-compose (mosquitto `command:`)
2. Update all MQTT broker nodes in Node-RED flows to use credentials
3. Credentials managed in `infrastructure/mosquitto/config/passwd` and `acl`

## Suricata Rules

Four rule modes available (switch via `command:` in docker-compose):

| File | Mode | Behavior |
|------|------|----------|
| `local.rules` | IDS (Alert) | Default — generates alerts only |
| `local.rules.ids` | IDS (Alert) | Alert-only rules |
| `local.rules.ips` | IPS (Drop) | Drops malicious packets |
| `local.rules.vuln` | Vulnerable | Rules disabled, no detection |

Switch by changing the mounted rules file:
```yaml
# In docker-compose.yaml suricata service:
volumes:
  - ./infrastructure/suricata/local.rules.ips:/etc/suricata/rules/local.rules  # Use IPS mode
```

## Portability

This project is designed to run on any machine with Docker:

- **No hardcoded absolute paths** — all volumes use relative paths or configurable env vars
- **Configurable network subnet** — set `IOT_SUBNET` in `.env` if 172.18.0.0/24 conflicts
- **Configurable project path** — set `IOT_PROJECT_PATH` in `.env` for host bind mounts
- **Cross-platform setup** — `scripts/setup.sh` (Linux/macOS) and `scripts/setup.ps1` (Windows)
- **Pinned image versions** — no `:latest` tags, reproducible deployments

For Docker Desktop users: set `IOT_PROJECT_PATH` to the full path using forward slashes (e.g., `C:/Users/user/IoT_InfraLab`).

## Troubleshooting

**InfluxDB fails to start or crashes:**
- Ensure all `DOCKER_INFLUXDB_INIT_*` vars are set in `.env`
- If re-deploying with existing volume: remove `influxdb_data` volume (`docker compose down -v influxdb`)
- Check token is valid 32-byte hex

**Node-RED can't create sensor containers:**
- Verify `IOT_PROJECT_PATH` in `.env` points to the project root
- Check docker-proxy is running: `docker compose ps docker-proxy`
- Ensure Docker socket proxy has POST and CONTAINERS permissions enabled

**Grafana dashboards show no data:**
- Verify InfluxDB datasource configured correctly (org: infralab, bucket: sensor_data)
- Check Telegraf is running and connected to InfluxDB
- Run `python gen_dashboards.py` to regenerate dashboard JSONs

**Suricata not detecting attacks:**
- Check Suricata logs: `docker compose logs suricata`
- Verify network interface: Suricata runs in `network_mode: service:mosquitto`
- Ensure rules file is mounted correctly
- Run security auditor: `docker compose up -d security-auditor`

## Configuration Reference

| Config File | Purpose |
|-------------|---------|
| `docker-compose.yaml` | Service orchestration, networks, volumes |
| `.env` | Secrets and runtime configuration |
| `config/sensor_settings.json` | Sensor type definitions and profiles |
| `infrastructure/suricata/suricata.yaml` | Suricata IDS/IPS engine config |
| `infrastructure/otel/otel-config.yaml` | OpenTelemetry pipeline |
| `infrastructure/promtail/promtail-config.yaml` | Log shipping to Loki |
| `infrastructure/tempo/tempo-config.yaml` | Trace storage config |
| `infrastructure/telegraf/telegraf.conf` | Docker host metrics collection |
| `infrastructure/grafana/provisioning/` | Grafana datasources and dashboards |
