# Grafana Dashboards

## Purpose

Three auto-provisioned Grafana dashboards providing visualization for IoT sensor telemetry, platform health, and security operations. All dashboards are generated programmatically via `gen_dashboards.py`.

## Datasources

Auto-provisioned from `infrastructure/grafana/provisioning/datasources/datasources.yaml`:

| Datasource | Type | URL | UID | Default |
|-----------|------|-----|-----|---------|
| InfluxDB | InfluxDB | `http://influxdb:8086` | `InfluxDB` | Yes |
| Loki | Loki | `http://loki:3100` | `Loki` | No |
| Tempo | Tempo | `http://tempo:3200` | `Tempo` | No |

## Dashboard 1: IoT Sensors Overview

**File:** `infrastructure/grafana/provisioning/dashboards/iot_sensors.json`
**UID:** `iot-sensors-overview`
**Source:** InfluxDB (`sensor_data` bucket)

### Variables
| Variable | Definition |
|----------|-----------|
| `sensor_id` | Tag values |
| `sensor_type` | Tag values |
| `profile` | Tag values |

### Panels (15 total)

**Stat panels:**
- Active Sensors — unique sensor count
- Data Points/min — aggregate window count
- Sensors With Dropouts — elapsed >30s between readings
- Current Avg Temperature — last 30s average
- Spikes Detected — count of `profile == "erratic"`
- Failing Sensors Count — distinct sensors with `profile == "failing"`

**Timeseries panels:**
- Temperature (°C, mean)
- Vibration (2 decimal precision)
- Power Draw (watts)
- Avg Temperature by Sensor (grouped by sensor_id)
- Avg Vibration by Sensor (grouped by sensor_id)
- Profile Comparison — temperature by profile (normal/failing/erratic)
- Spike Detection — erratic profile + temperature
- 5-min Rolling Average — `timedMovingAverage`

**Table panel:**
- Sensors by Zone — pivot by sensor_type

## Dashboard 2: Platform Health

**File:** `infrastructure/grafana/provisioning/dashboards/platform_health.json`
**UID:** `platform-health`
**Source:** InfluxDB (`platform_metrics` bucket, populated by Telegraf)

### Variables
| Variable | Definition |
|----------|-----------|
| `service` | Container name from Docker input |

### Panels (9 total)
- Host CPU Utilization — `100 - usage_idle`, percent unit
- Host Memory Usage — bytes
- System Load Average — load1
- Host Network Throughput — derivative of bytes_recv/bytes_sent, Bps
- Host Disk I/O — derivative of read_bytes/write_bytes
- Per-Container CPU — `docker_container_cpu`, usage_percent
- Per-Container Memory — `docker_container_mem`, usage
- Per-Container Network — `docker_container_net`, rx/tx derivative
- Service Status Table — last usage by container_name

## Dashboard 3: Security Operations (SOC)

**File:** `infrastructure/grafana/provisioning/dashboards/security.json`
**UID:** `security-operations`
**Source:** Loki (Suricata alert logs)

### Variables
| Variable | Definition |
|----------|-----------|
| `attack_type` | Alert signature values |
| `src_ip` | Source IP values |

### Panels (11 total)

**Stat panels:**
- Total Alerts — `count_over_time`
- Alert Rate — `rate`
- IPS Mode — severity=3 alert count
- Active MQTT Connections — mosquitto "New connection" log count
- Unique Attackers — distinct src_ip count
- Severity 1 — critical alert count

**Visualization panels:**
- Alert Timeline — timeseries, sum by alert_severity
- Alert Severity Breakdown — piechart (critical=1, high=2, medium=3)
- Top Attacker IPs — table, sum by src_ip
- Attack Type Distribution — bar gauge, sum by alert_category

**Log panels:**
- Recent Alerts — formatted lines with severity, src/dest, signature
- Mosquitto Broker Log — raw `{job="mosquitto"}`

## Dashboard Provisioning

Dashboards are auto-provisioned at Grafana startup via:

```yaml
# infrastructure/grafana/provisioning/dashboards/dashboards.yaml
apiVersion: 1
providers:
  - name: "default"
    orgId: 1
    folder: ""
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

## Dashboard Generator

All three dashboards are generated from `gen_dashboards.py` — a Python script using dict templates:

```powershell
python test/gen_dashboards.py
```

Benefits of programmatic generation:
- **Consistency** — shared panel templates across dashboards
- **Version control** — changes tracked in Python, not opaque JSON
- **Easy updates** — modify queries or add panels in one place

## Related

- Dashboard generator code: [17-dashboard-generator.md](17-dashboard-generator.md)
- Observability stack: [09-observability-stack.md](09-observability-stack.md)
- InfluxDB schema: [12-influxdb-schema.md](12-influxdb-schema.md)
