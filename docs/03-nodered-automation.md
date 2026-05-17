# Node-RED Automation

## Purpose

Visual flow automation platform providing the primary user interface for sensor management, security operations, and cyber attack simulation. Acts as the orchestrator connecting MQTT, Docker API, and InfluxDB.

## Configuration

**Image:** `nodered/node-red:latest`
**Container:** `iot_nodered`
**User:** `root`
**IP:** `172.18.0.25` (static)
**Port:** 1880
**Memory:** 384 MB limit / 256 MB reserved

### Node.js Tuning

```
NODE_OPTIONS=--max-old-space-size=256 --max-semi-space-size=2
```

Limits heap to 256 MB and young generation to 2 MB — critical for memory-constrained environment.

### Data Persistence

- Flows: `src/simulation/nodered/NodeRed_Data/flows.json`
- Credentials: `flows_cred.json` (encrypted with `NODE_RED_CREDENTIAL_SECRET` from `.env`)
- Active sensors: `sensors.json`
- Saved profiles: `saved_sensors.json` (10 factory configurations)
- Settings: `settings.json`

## Flow Architecture (4 Tabs)

### 1. Node Management
Full lifecycle control for simulated IoT sensors:

1. **Define** — select sensor type from blueprints (temperature, humidity, pressure, vibration, power)
2. **Configure** — assign ID, type combination, behavior profile, publish interval
3. **Deploy** — Docker API creates container running `simulator.py`
4. **Monitor** — live MQTT feed in dashboard UI
5. **Control** — start, stop, pause, restart, kill individual sensors

### 2. Security Ops
- **Network topology** — live container map via Docker API polling
- **Suricata alerts** — real-time IDS/IPS alert stream via docker exec reading eve.json
- **IPS mode toggle** — switch between alert (IDS), drop (IPS), and passive (vuln) rule sets
- **AI audit** — trigger security auditor nmap + Gemini scan
- **NAC** — isolate suspicious containers from `iot_infralab_net`

### 3. Cyber Attack Simulation
5-phase killchain with per-stage buttons:

| Phase | Action | Method |
|-------|--------|--------|
| 0 | Create Attacker | Docker API create container |
| 1 | Breach Network | Docker network connect |
| 2 | Reconnaissance | docker exec nmap |
| 3 | Sniff MQTT | docker exec mqtt_sniff.py |
| 4 | Impact | docker exec hping3 / mqtt_dos.py |
| 5 | Remove Traces | Docker API kill + rm container |

### 4. Backend
- MQTT-to-InfluxDB data pipeline
- Format Data function node — transforms MQTT JSON to InfluxDB line protocol
- System interconnects and MQTT broker connections

## Docker Integration

Node-RED communicates with `docker-proxy:2375` via HTTP Request nodes:

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| List containers | GET | `/containers/json` |
| Create container | POST | `/containers/create` |
| Start container | POST | `/containers/{id}/start` |
| Stop container | POST | `/containers/{id}/stop` |
| Remove container | DELETE | `/containers/{id}` |
| Exec command | POST | `/containers/{id}/exec` |

## Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `@flowfuse/node-red-dashboard` | ~1.30.2 | Dashboard 2.0 UI framework |
| `node-red-contrib-dockerode` | ~0.15.0 | Docker API wrapper nodes |
| `node-red-contrib-influxdb` | ~0.7.0 | InfluxDB write/query nodes |

## MQTT Brokers

Two broker connections configured:
- **Makmal MQTT Broker** — `mosquitto:1883`, client ID `nodered_monitor_client`
- **Mosquitto Broker** — `iot_broker:1883`
- **MQTT Out node** — publishes to `sensors/factory/{sensor_id}`, QoS 1

## InfluxDB Integration

- **Server:** `http://influxdb:8086`
- **Version:** 2.0 (Flux query)
- **Organization:** `infralab`
- **Bucket:** `sensor_data`
- **Measurement:** `sensor_data`
- **Tags:** `sensor_id`, `sensor_type`, `profile`
- **Precision:** milliseconds

The Format Data function node (id `0a3d5de1d4fa2473`) transforms:
```json
{"temperature": 28.5, "vibration": 0.123}
```
→ InfluxDB line protocol with value field and tag extraction.

## Guided Tours

Three Driver.js interactive overlays:
- **Node Management:** 30 steps across 7 UI groups
- **Security Ops:** 15 steps across 4 UI groups  
- **Cyber Attack Simulation:** 9 steps across 2 UI groups

Tours persist dismissal via `localStorage`. Re-enable from `/dashboard/helps` page.

## Related

- Sensor profiles: [05-sensor-simulation.md](05-sensor-simulation.md)
- Docker proxy: [04-docker-proxy.md](04-docker-proxy.md)
- Attack simulation: [06-attack-simulation.md](06-attack-simulation.md)
