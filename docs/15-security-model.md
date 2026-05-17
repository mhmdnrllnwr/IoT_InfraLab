# Security Model

## Purpose

This lab intentionally uses insecure configurations to enable realistic attack/defense scenarios for educational security testing. This document categorizes each vulnerability, its rationale, and the hardening path to close it.

## Attack Surface Overview

```
Internet ──→ [Host Ports] ──→ Internal Services
                                   │
                          ┌────────┴────────┐
                          │  Vulnerabilities │
                          │  - Anonymous MQTT│
                          │  - Docker API    │
                          │  - Weak creds    │
                          │  - Plaintext     │
                          └─────────────────┘
```

## Intentional Vulnerabilities

### 1. Anonymous MQTT Access

| Detail | Value |
|--------|-------|
| **Location** | `mosquitto:1883` — `mosquitto_vulnerable.conf` |
| **Setting** | `allow_anonymous true` |
| **Attack Enabled** | MQTT sniffing (`#` subscribe), injection (publish any topic), DoS (connection exhaustion) |

**Why it exists:** Anonymous access is the foundational vulnerability enabling all MQTT-based attack scenarios. Without it, the attacker cannot eavesdrop or inject telemetry.

**Detection in action:** Suricata's rogue subscriber rule (sid:1000007) detects `#` wildcard subscriptions. SYN flood rule (sid:1000001) detects connection floods.

**Hardening:** Switch to `mosquitto_hardened.conf` (password_file + acl_file enforced). Requires updating Node-RED MQTT broker credentials and rebuilding flow credentials.

### 2. Docker API POST/DELETE/EXEC

| Detail | Value |
|--------|-------|
| **Location** | `docker-proxy` environment flags |
| **Setting** | `POST=1`, `DELETE=1`, `EXEC=1` |
| **Attack Enabled** | Container lifecycle abuse, kill switch, arbitrary command execution |

**Why it exists:** Node-RED needs these permissions for sensor lifecycle management (create/start/stop containers), exec commands for attack simulation, and network management.

**Why a proxy (not direct socket):** The docker-socket-proxy provides fine-grained API control. Direct `/var/run/docker.sock` mount would give Node-RED unfiltered Docker daemon access.

**Hardening:** Remove `DELETE=1` and `EXEC=1` if not needed. The proxy is already internal-only (no external port).

### 3. Weak Grafana Credentials

| Detail | Value |
|--------|-------|
| **Location** | `.env` |
| **Credentials** | `admin123` / `admin123` |
| **Attack Enabled** | Dashboard tampering, data access |

**Why it exists:** Demo simplicity. The Grafana instance is only accessible via `localhost:3000`.

**Hardening:** Change `GF_SECURITY_ADMIN_PASSWORD` in `.env`.

### 4. Plaintext Protocols

| Detail | Value |
|--------|-------|
| **Scope** | All services (MQTT, OTLP, HTTP, Docker API) |
| **Attack Enabled** | Packet capture reveals all data and credentials |

**Why it exists:** TLS would prevent Suricata from inspecting MQTT payloads. Plaintext enables full observability of the attack surface.

**Hardening:** Add TLS termination at service level. Note: Suricata MQTT inspection will break if traffic is encrypted.

## Defense Layers

```
Layer 1: Suricata IDS/IPS
  ├── IDS mode: Alert on malicious patterns
  ├── IPS mode: Actively block attacks (TCP RST)
  └── 3 rule sets: Alert / Drop / Passive (swappable at runtime)

Layer 2: SOC Dashboard (Grafana + Loki)
  ├── Real-time alert timeline
  ├── Attacker IP tracking
  └── Severity-based triage

Layer 3: AI Security Auditor
  ├── Automated nmap scan
  ├── Gemini-powered vulnerability analysis
  └── On-demand execution from Node-RED

Layer 4: Container Isolation (NAC)
  ├── Disconnect suspicious containers from network
  └── Executed manually from Node-RED Security Ops
```

## IPS Mode Behavior

When IPS mode is active (local.rules.ips):
- Detection rules use `drop` action instead of `alert`
- Suricata sends TCP RST to attacking source
- MQTT attack scripts detect disconnection via `on_disconnect` callback
- Legitimate traffic from safelisted IPs is still passed

## Hardening Checklist

For production-adjacent deployment:

- [ ] Switch Mosquitto to `mosquitto_hardened.conf`
- [ ] Update Node-RED MQTT broker nodes with credentials
- [ ] Rebuild Node-RED flow credentials (`flows_cred.json`)
- [ ] Remove `DELETE=1` from docker-proxy if kill switch not needed
- [ ] Remove `EXEC=1` from docker-proxy if not needed
- [ ] Change Grafana admin password in `.env`
- [ ] Add TLS for MQTT (assess IDS impact)
- [ ] Add TLS for OTLP (Tempo + Collector)
- [ ] Restrict host port exposures to specific IPs
- [ ] Set Grafana to require authentication for all users

## Related

- Mosquitto config: [02-mqtt-broker.md](02-mqtt-broker.md)
- Docker proxy: [04-docker-proxy.md](04-docker-proxy.md)
- Suricata rules: [08-suricata-ids-ips.md](08-suricata-ids-ips.md)
- Attack simulation: [06-attack-simulation.md](06-attack-simulation.md)
