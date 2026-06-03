# Cloud Deployment — IoT_InfraLab

## GCP (Google Cloud Platform)

### Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Sufficient quota for 1 VM + network resources

### OS Selection

**Use Ubuntu 22.04 LTS.** Do NOT use Container-Optimized OS (COS) — it lacks `apt`/package manager and requires additional tooling to install Docker.

### Deployment

```bash
# Make script executable
chmod +x cloud/gcp-setup.sh

# Edit variables in gcp-setup.sh: PROJECT_ID, ZONE, MACHINE_TYPE
# Then run
bash cloud/gcp-setup.sh
```

### Firewall Rules

The setup script opens these ports:

| Port | Service | Purpose |
|------|---------|---------|
| 1880 | Node-RED | Flow editor & dashboard |
| 3000 | Grafana | Metrics dashboards |
| 8086 | InfluxDB | Time-series API |
| 22 | SSH | Administration |

All ports restricted to `0.0.0.0/0`. Restrict to your IP in production.

### SSH Access

```bash
gcloud compute ssh iot-infralab-vm --zone <your-zone>
```

Once connected, the stack is at `~/IoT_InfraLab/`. Use `docker compose` commands inside the VM.

### Post-Deploy

1. **Set `IOT_PROJECT_PATH`** — Edit `.env` on the VM, set `IOT_PROJECT_PATH=/home/ubuntu/IoT_InfraLab` (must be absolute path on Linux). Docker Desktop's `.` auto-resolve doesn't work on cloud VMs.
2. **Fill secrets** — Set `GEMINI_API_KEY`, generate `INFLUXDB_TOKEN` with `openssl rand -hex 32`, change all passwords.
3. **Start stack** — `docker compose build security-auditor nodered && docker compose up -d`
4. **Create InfluxDB buckets** — `bash scripts/setup-influxdb.sh` (creates all 4 buckets)
5. Access UIs via VM's external IP.

### Notes

- VM size: `e2-standard-2` (2 vCPU, 8 GB) is minimum for full stack
- Boot disk: 20 GB SSD
- Stack uses ~2.5 GB RAM, ~1.5 GB disk for data volumes
