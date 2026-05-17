# Attack Simulation (docker_attacker)

## Purpose

Containerized attack toolkit for demonstrating a realistic 5-stage cyber killchain against the IoT infrastructure. Each stage is executable from the Node-RED Cyber Attack Simulation dashboard.

## Container

**Image:** `docker-attacker` (built from `src/simulation/docker_attacker/Dockerfile`)
**Base:** `python:3.9-alpine`
**CMD:** `/bin/sh` (stays alive for docker exec commands)

### Installed Tools

| Tool | Purpose |
|------|---------|
| `nmap` | Network reconnaissance |
| `curl` | HTTP requests |
| `iproute2` | Network interface management |
| `tcpdump` | Packet capture |
| `python3` + `paho-mqtt` | MQTT attack scripts |

## Attack Scripts

### mqtt_sniff.py
Subscribes to MQTT `#` wildcard topic, dumps all messages to console. Detects Suricata IPS intervention via `on_disconnect` callback — when Suricata drops malicious traffic (TCP RST), the script reports the disconnection.

### mqtt_inject.py
Publishes fake JSON telemetry to `sensors/data` with `"fake_injection": true` flag. Demonstrates MQTT injection vulnerability in anonymous mode.

### mqtt_dos.py
Launches configurable concurrent MQTT connections (default 50 threads). Each thread maintains a connection and publishes garbage to `sensors/flood` at 0.01s intervals. Configurable via `--threads` argument.

## 5-Stage Killchain

| Stage | Action | Method | Tool |
|-------|--------|--------|------|
| 0 | Create Attacker | Docker API POST `/containers/create` | Node-RED HTTP Request |
| 1 | Breach Network | Docker API POST `/networks/{id}/connect` | Node-RED HTTP Request |
| 2 | Reconnaissance | docker exec nmap scan `172.18.0.0/24` | `nmap -sT -T4` |
| 3 | Sniff MQTT | docker exec subscribe to `#` | `mqtt_sniff.py` |
| 4 | Impact | SYN flood or app-layer DoS | `hping3` or `mqtt_dos.py` |
| 5 | Remove Traces | Docker API DELETE container | Node-RED HTTP Request |

## What Each Stage Demonstrates

1. **Container escape / abuse** — unauthorized container creation via Docker API
2. **Network lateral movement** — breaching internal network boundaries
3. **Reconnaissance** — service discovery and port scanning
4. **Eavesdropping** — MQTT traffic interception (plaintext, anonymous)
5. **Denial of Service** — both network-layer (SYN flood) and application-layer (MQTT connection exhaustion)

## Related

- Suricata detection rules for attack patterns: [08-suricata-ids-ips.md](08-suricata-ids-ips.md)
- Simulation execution: [03-nodered-automation.md](03-nodered-automation.md)
- Security model context: [15-security-model.md](15-security-model.md)
