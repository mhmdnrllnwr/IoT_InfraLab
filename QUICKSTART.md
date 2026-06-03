# IoT_InfraLab — Quick Start

5-step setup for IoT cybersecurity simulation lab.

## 1. Prerequisites

- Docker 24.0+ with Compose v2
- 4 GB free RAM
- Git

## 2. Clone & Configure

```bash
git clone <repo-url> IoT_InfraLab
cd IoT_InfraLab

# Generate secure values and create .env
openssl rand -hex 32   # Use output as INFLUXDB_TOKEN
openssl rand -hex 16   # Use output as NODE_RED_CREDENTIAL_SECRET
cp .env.example .env
```

Edit `.env`: Set `GEMINI_API_KEY`, `INFLUXDB_TOKEN`, `NODE_RED_CREDENTIAL_SECRET`, and passwords.

## 3. Build & Start

```bash
# Build custom images
docker compose build security-auditor nodered

# Validate and start
docker compose config
docker compose up -d
```

## 4. Verify

```bash
docker compose ps                  # All 12 services Up
python test/smoke_test.py          # All 5 checks pass
```

| URL | Service |
|-----|---------|
| http://localhost:1880 | Node-RED Editor |
| http://localhost:1880/dashboard | Node-RED Dashboard |
| http://localhost:3000 | Grafana (admin / your_password) |
| http://localhost:8086 | InfluxDB |

## 5. Generate Data

1. Deploy 2-3 sensors from Node-RED **Node Management** tab
2. Trigger AI audit from **Security Ops** tab
3. Run attack simulation from **Cyber Attack Simulation** tab
4. Wait 2-3 minutes for data to appear in Grafana

## Common Fixes

**InfluxDB blank / no bucket:**
```bash
# Run setup script (creates all 4 buckets idempotently)
# Linux:
bash scripts/setup-influxdb.sh
# Windows:
powershell scripts/setup-influxdb.ps1

# If bucket still missing, clear volume and restart:
docker compose down -v influxdb
docker compose up -d influxdb
# Then run setup script again
```

**Node-RED dashboard blank (missing palette nodes):**
```bash
docker compose restart nodered
# Check logs: docker compose logs nodered | grep "npm install"
```

**Grafana shows "Datasource not found":**
```bash
docker compose restart grafana
# Wait 30s for provisioning to reload
```
