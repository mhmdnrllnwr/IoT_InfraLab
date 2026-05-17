# Testing & Verification

## Purpose

Procedures for verifying the system is functioning correctly after deployment or changes. Covers automated smoke tests and manual verification steps.

## Automated Smoke Test

**File:** `test/smoke_test.py`

```powershell
python test/smoke_test.py
```

### Check Sequence

| # | Check | What It Validates |
|---|-------|-------------------|
| 1 | MQTT Broker | Mosquitto reachable on port 1883, accepts connections |
| 2 | InfluxDB | HTTP 200 on `/health`, API available |
| 3 | Grafana | HTTP 200 on `/api/health`, dashboards available |
| 4 | Node-RED | HTTP 200 on `/`, flows running |
| 5 | Data Pipeline | MQTT → InfluxDB flow: publish test message, verify write |

### Expected Output

```
[1/5] MQTT Broker ......... OK
[2/5] InfluxDB ............ OK
[3/5] Grafana ............. OK
[4/5] Node-RED ............ OK
[5/5] Data Pipeline ....... OK
```

## Docker Compose Validation

After any change to `docker-compose.yaml`:

```powershell
docker compose config
```

Validates the compose file syntax and resolves all variables. Exit code 0 means valid.

## Service Health

```powershell
docker compose ps
```

Expected: all 12 services showing `Up` status.

## Per-File Validation

### Python files
```powershell
python -m py_compile src/simulation/docker_sensor/simulator.py
python -m py_compile src/simulation/auditor_security/auditor.py
python -m py_compile test/smoke_test.py
python -m py_compile gen_dashboards.py
```

### YAML files
Verify structure — no dedicated linter, manual review for:
- Correct indentation (2 spaces)
- Valid key names
- Proper array syntax

### JSON files
```powershell
python -m json.tool config/sensor_types.json > $null
python -m json.tool config/sensor_settings.json > $null
python -m json.tool infrastructure/grafana/provisioning/dashboards/iot_sensors.json > $null
```

## Manual Verification

### 1. Sensor Deployment
1. Open Node-RED Dashboard: `http://localhost:1880/dashboard`
2. Navigate to Node Management tab
3. Create and deploy a sensor
4. Verify container appears: `docker ps | findstr "sensor"`
5. Verify MQTT data: check live feed in dashboard

### 2. Grafana Dashboards
1. Open Grafana: `http://localhost:3000` (admin123/admin123)
2. Verify IoT Sensors Overview shows data
3. Verify Platform Health shows metrics
4. Verify SOC dashboard shows alerts (may need to trigger attacks first)

### 3. Attack Simulation
1. Navigate to Cyber Attack Simulation tab in Node-RED
2. Execute Stage 0 (Create Attacker)
3. Verify alert in Grafana SOC Dashboard (Suricata detects nmap)
4. Execute Stages 1-5
5. Verify alerts for each attack phase

### 4. Distributed Traces
1. Grafana → Explore → Tempo datasource
2. Query: `{service.name="security-auditor"}`
3. Verify trace spans visible
4. Click individual spans for timing and attributes

### 5. Log Pipeline
1. Grafana → Explore → Loki datasource
2. Query: `{job="suricata"}`
3. Verify alert log entries visible
4. Filter by event_type: `{job="suricata"} |= "alert"`

## Build Verification

For container changes:

```powershell
docker compose build <service>
```

Test after rebuild:

```powershell
docker compose up -d --build <service>
docker compose logs <service>
```

## Related

- Deployment guide: [19-deployment-guide.md](19-deployment-guide.md)
- Smoke test file: `test/smoke_test.py`
- Dashboard verification: [10-grafana-dashboards.md](10-grafana-dashboards.md)
