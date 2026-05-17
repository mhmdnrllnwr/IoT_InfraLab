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

```powershell
git clone <repo-url> IoT_InfraLab
cd IoT_InfraLab
```

### 2. Configure Environment

Create/edit `.env`:

```
# Required: InfluxDB admin token (auto-generated for first run)
INFLUXDB_TOKEN=your_super_secret_token

# Required: Node-RED credential encryption
NODE_RED_CREDENTIAL_SECRET=change_this_secret

# Optional: Gemini API key (skip for degraded mode)
GEMINI_API_KEY=

# Grafana admin password
GF_SECURITY_ADMIN_PASSWORD=admin123
```

Leave `GEMINI_API_KEY` blank to run without AI analysis — auditor performs nmap scans but skips Gemini.

### 3. Start the Stack

```powershell
docker compose up -d
```

### 4. Verify All Services

```powershell
docker compose ps
```

Expected output: all 12 services with `Up` status.

### 5. Run Smoke Test

```powershell
python test/smoke_test.py
```

All 5 checks should pass.

### 6. Set Up InfluxDB (first run only)

```powershell
# If buckets/org not auto-created
powershell -File scripts/setup-influxdb.ps1
```

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
