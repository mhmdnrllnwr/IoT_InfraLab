# Deployment Guide

## Purpose

Step-by-step instructions for deploying the full IoT InfraLab stack from scratch. Covers prerequisites, setup, startup, and common troubleshooting.

## Prerequisites

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| Docker Desktop | 4.30+ | Latest stable |
| Docker backend | WSL2 | WSL2 (Ubuntu 22.04) |
| RAM allocated to Docker | 8 GB | 12 GB |
| Disk space | 10 GB | 20 GB |
| Git | Any recent version | Latest |
| Gemini API key | Optional | For AI auditor |

## Deployment Steps

### 1. Clone Repository

```bash
git clone <repo-url> IoT_InfraLab
cd IoT_InfraLab
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Required variables:
- `GEMINI_API_KEY` — Google Gemini API key (from Google AI Studio). Leave blank to skip AI analysis (degraded mode).
- `INFLUXDB_TOKEN` — Generate with `openssl rand -hex 32`
- `NODE_RED_CREDENTIAL_SECRET` — Generate with `openssl rand -hex 16`
- `GF_SECURITY_ADMIN_PASSWORD` — Grafana admin password

**Linux/cloud:** Set `IOT_PROJECT_PATH` to absolute path (e.g. `/home/user/IoT_InfraLab`). Docker Desktop can leave as `.` (auto-resolves).

### 3. Build Custom Images

```bash
docker compose build security-auditor nodered
```

Security auditor and Node-RED have custom Dockerfiles. Other services use pre-built images.

### 4. Start the Stack

```bash
# Validate configuration
docker compose config

# Start all services
docker compose up -d

# Check all 12 services Up
docker compose ps
```

### 5. Create InfluxDB Buckets

First run creates `sensor_data` bucket automatically. Create all 4 buckets:

```bash
# Linux:
bash scripts/setup-influxdb.sh

# Windows:
powershell -File scripts/setup-influxdb.ps1
```

This creates `sensor_data`, `sensor_saved`, `sensor_metadata`, `platform_metrics` idempotently.

### 6. Run Smoke Test

```bash
pip install -r requirements.txt
python test/smoke_test.py
```

All 5 checks should pass.

### 7. Access UIs

| Service | URL | Credentials |
|---------|-----|-------------|
| Node-RED Dashboard | `http://localhost:1880/dashboard` | None |
| Node-RED Editor | `http://localhost:1880` | None (add auth in settings if needed) |
| Grafana | `http://localhost:3000` | `admin123` / `admin123` |

## Common Operations

### Rebuild and Restart a Service

```powershell
docker compose up -d --build security-auditor
```

### View Logs

```powershell
docker compose logs -f suricata
docker compose logs -f security-auditor
docker compose logs -f loki
```

### Stop Stack (preserve data)

```powershell
docker compose down
```

### Stop Stack (delete all data)

```powershell
docker compose down -v   # CAUTION: removes named volumes
```

### Scale Sensors

Sensors are created dynamically from Node-RED — no compose scaling needed.

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Container exits immediately | Memory limit too low | Check logs: `docker compose logs <service>`; increase limits in compose |
| Suricata no alerts | Wrong network mode | Verify `network_mode: service:mosquitto` in compose |
| Gemini AI returns errors | Missing API key or quota | Check `GEMINI_API_KEY` in `.env`; verify billing in Google AI Studio |
| Sensor containers can't start | Docker proxy not ready | `docker compose restart docker-proxy` |
| Blank Grafana dashboards | No data in InfluxDB/Loki | Deploy sensors via Node-RED; run attack simulation to generate alerts |
| OTEL traces not visible | Collector not receiving | `docker compose logs otel-collector`; check reachability to tempo:4317 |
| Named volume data loss | `docker compose down -v` | Use `docker compose down` without `-v` to preserve volumes |
| Promtail no logs | Suricata not writing eve.json | Check `infrastructure/suricata/logs/eve.json` exists and has content |
| Port conflict | Another service using same port | Change host port in compose or stop conflicting service |
| InfluxDB bucket missing | Existing bolt.db blocks re-init | `bash scripts/setup-influxdb.sh` or clear volume: `docker compose down -v influxdb` then restart |

## Cloud Deployment

See `cloud/README.md` for GCP deployment instructions. Use Ubuntu 22.04 — do NOT use Container-Optimized OS (lacks package manager).

## Initial Data Generation

After first startup, generate data to populate dashboards:

1. **Deploy 2-3 sensors** via Node-RED Node Management tab
2. **Trigger AI audit** from Security Ops tab
3. **Run attack simulation** from Cyber Attack Simulation tab
4. **Wait 2-3 minutes** for data to accumulate in InfluxDB and Loki

## Related

- Architecture overview: [01-architecture-overview.md](01-architecture-overview.md)
- Testing: [18-testing-verification.md](18-testing-verification.md)
- Configuration reference: [16-configuration-files.md](16-configuration-files.md)
