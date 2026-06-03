# IoT InfraLab — Acceptance Criteria

Each criterion defines a pass/fail test. All must pass for system acceptance.

---

## A. Stack Health

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| A-01 | Docker daemon reachable | `docker info` succeeds | `docker info` exit 0 |
| A-02 | 12 stack containers running | `docker ps` count | 12 containers with `Running` status |
| A-03 | Mosquitto accepts MQTT on :1883 | TCP connect | Response within 3s |
| A-04 | InfluxDB serves /health on :8086 | HTTP GET | 200 response |
| A-05 | Grafana serves /api/health on :3000 | HTTP GET | 200 response |
| A-06 | Node-RED serves / on :1880 | HTTP GET | 200 response |
| A-07 | Loki serves /ready on :3100 | HTTP GET | 200 response |
| A-08 | MQTT client can subscribe to lab/smoke/test | paho-mqtt connect + subscribe | No error |
| A-09 | iot-sensor image exists | `docker images iot-sensor` | Non-empty output |
| A-10 | iot_infralab_net exists | `docker network inspect` | Network found |

## B. Sensor Lifecycle

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| B-01 | Create sensor container via Docker CLI | `docker create` | Exit 0, returns container ID |
| B-02 | Start sensor container | `docker start` | Exit 0 |
| B-03 | Sensor connects to MQTT within 10s | Monitor `sensors/factory/{id}` | First message received ≤ 10s |
| B-04 | Sensor payload has valid structure | JSON parse | Contains `sensor_id`, `readings`, `timestamp` |
| B-05 | Sensor data arrives in InfluxDB within 30s | Flux query `sensor_data` bucket | Data points returned |
| B-06 | Sensor publishes at correct interval | Measure inter-message gap | ~5s |
| B-07 | Remove sensor container | `docker rm -f` | Exit 0, no orphans |
| B-08 | Zero bench_* containers remain after cleanup | `docker ps -a --filter name=bench_` | Zero results |

## C. Data Pipeline

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| C-01 | Grafana datasources include Loki, Tempo, InfluxDB | GET /api/datasources | 3 datasources with UIDs Loki, Tempo, InfluxDB |
| C-02 | Grafana dashboards include IoT, Platform, Security | GET /api/search | 3 dashboards titled correctly |
| C-03 | InfluxDB has `sensor_data` bucket | Flux `buckets()` query | Bucket exists |
| C-04 | InfluxDB has `platform_metrics` bucket | Flux `buckets()` query | Bucket exists |
| C-05 | Promtail ships Suricata logs to Loki | Loki LogQL `{job="suricata"}` | Results with `event_type` field |
| C-06 | OTel gRPC port 4317 responds | TCP connect | Connection accepted |

## D. Security Audit

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| D-01 | Security auditor container is running | `docker ps` | Shows `security_auditor` running |
| D-02 | Publish SCAN_NOW to lab/security/trigger | MQTT publish | No error |
| D-03 | Audit report published on lab/security/report | MQTT subscribe | Report received within 120s |
| D-04 | Report contains HTML table | String match | `<table>` tag present |
| D-05 | Audit status updates on lab/security/status | MQTT subscribe | ≥2 status messages during scan |

## E. Suricata Detection

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| E-01 | Suricata container is running | `docker ps` | Shows `suricata-ids` running |
| E-02 | Suricata eve.json exists and has alerts | File exists + jq query | Alerts with `event_type: alert` |
| E-03 | Nmap scan triggers Suricata alert | Run scan, check eve.json | Alert for scan detection appears |

## F. Attack Simulation

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| F-01 | MQTT inject publishes to sensors/data | Publish, subscribe to verify | Message received on topic |
| F-02 | MQTT sniff subscribes to wildcard # | Connect, subscribe `#` | No error, messages captured |
| F-03 | Mosquitto accepts anonymous publish | Publish without auth | Message accepted (vulnerable config) |

## G. Cleanup

| ID | Criterion | Method | Pass/Fail |
|----|-----------|--------|-----------|
| G-01 | Kill switch removes all iot-sensor containers | `docker rm -f $(docker ps -aq --filter ancestor=iot-sensor)` | Zero iot-sensor containers |
| G-02 | No bench_* containers remain | `docker ps -a --filter name=bench_` | Zero results |
| G-03 | `docker compose down` succeeds | Command | Exit 0, network removed |
