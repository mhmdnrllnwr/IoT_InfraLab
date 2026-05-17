# MQTT Broker (Mosquitto)

## Purpose

Central message broker for all IoT telemetry and inter-service communication. All sensor data, security events, and system commands flow through Mosquitto.

## Configuration

**Image:** `eclipse-mosquitto:2.0`
**Container:** `iot_broker`
**Ports:** 1883 (MQTT), 9001 (WebSocket)
**Memory:** 64 MB limit

Two configuration files exist in `infrastructure/mosquitto/config/`:

### Active: mosquitto_vulnerable.conf

```
listener 1883
allow_anonymous true
```

Anonymous access enabled — no authentication required. This is **intentional** for security testing.

### Alternative: mosquitto_hardened.conf

```
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwd
acl_file /mosquitto/config/acl
```

Enforces password authentication and topic-level ACLs.

## Why Anonymous Access

| Attack Scenario | What It Enables |
|----------------|-----------------|
| MQTT Sniffing | Anyone can subscribe to `#` wildcard and capture all telemetry |
| MQTT Injection | Anyone can publish fake telemetry to any topic |
| Application DoS | Attackers can exhaust broker connection pools |

TLS is intentionally avoided — Suricata (sharing the broker's network namespace) can inspect plaintext MQTT payloads in real time. TLS would blind the IDS.

## Topic Structure

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `sensors/factory/{sensor_id}` | Sensor → Broker | Telemetry data |
| `lab/security/trigger` | Node-RED → Auditor | Trigger security scan |
| `lab/security/model` | Node-RED → Auditor | AI model selection |
| `lab/security/report` | Auditor → Node-RED | Scan results |
| `lab/security/status` | Auditor → Node-RED | Heartbeat/status |
| `cmd/system/reload` | Node-RED → Sensors | Config reload command |

## Credentials (Hardened Mode)

File: `infrastructure/mosquitto/config/passwd`

| User | Type | ACL Scope |
|------|------|-----------|
| `admin` | Full access | `readwrite #` |
| `sensor` | Write-only | `write telemetry/#` |
| `dashboard` | Read-only | `read telemetry/#` |

File: `infrastructure/mosquitto/config/acl` — defines topic-level read/write restrictions per user.

## Data Flow

```
Sensor → publish sensors/factory/{id} → Mosquitto
  → Node-RED (subscribed) → InfluxDB Out → InfluxDB
  → Promtail ships eve.json → Loki (for any MQTT auth failures in hardened mode)
```

## Related

- Hardening guide: [15-security-model.md](15-security-model.md)
- Sensor data format: [05-sensor-simulation.md](05-sensor-simulation.md)
- Attack scenarios using MQTT: [06-attack-simulation.md](06-attack-simulation.md)
