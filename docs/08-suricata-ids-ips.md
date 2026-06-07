# Suricata IDS/IPS

## Purpose

Network intrusion detection and prevention system inspecting all traffic through the MQTT broker. Provides real-time alerting on malicious activity and can actively block attacks (IPS mode).

## Container

**Image:** `jasonish/suricata:latest`
**Container:** `suricata-ids`
**Network Mode:** `service:mosquitto` — shares Mosquitto's network namespace
**Memory:** 256 MB
**User:** `root`
**Capabilities:** `NET_ADMIN`, `NET_RAW`, `SYS_NICE`

### Critical Config Rule

```
stream:
  checksum-validation: no
```

This is **required** under WSL2. Hyper-V virtual switches rewrite TCP checksums, causing Suricata to see invalid checksums on every packet. Without this, Suricata drops all traffic — becoming "Blind IDS."

### Output

```
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      types: [alert, http, mqtt, drop]
  output-flush-interval: 1
```

Flushes `eve.json` every 1 second for real-time alerting. Promtail ships these to Loki.

## Five Rule Sets

Suricata mounts five rule files. Node-RED switches between them at runtime via docker exec + Suricata signal handling.

### local.rules — Default Mode (active by default)

Default IDS rule set loaded at `/etc/suricata/rules/local.rules`. Full detection with `alert` action.

| SID | Rule | Detection | Action |
|-----|------|-----------|--------|
| 9900001-3 | Safelist | Known-good IPs (Auditor, Node-RED, Promtail) | `pass` |
| 1000001 | MQTT SYN Flood | >100 SYN packets/sec from single source to port 1883 | `alert` |
| 1000002 | Nmap SYN Stealth Scan | >20 SYNs in 5 seconds from single source | `alert` |
| 1000003 | Protocol Mismatch | HTTP methods (GET/POST/PUT/DELETE) on MQTT port 1883 | `alert` |
| 1000005 | Rogue Subscriber (native) | MQTT parser matches subscribe topic `#` wildcard | `alert` |
| 1000007 | Rogue Subscriber (raw) | Raw hex `00 01 23` (MQTT subscribe with `#` wildcard) | `alert` |
| 1000009 | MQTT App DoS | >50 msgs/sec from single source to MQTT broker | `alert` |
| 1000010 | Fake Telemetry | Payload contains `"fake_injection"` string | `alert` |

### local.rules.ids — IDS Mode (dedicated file)

Same rules as default — provided as a dedicated file for explicit IDS-only mode switching.

### local.rules.ips — Drop Mode

Same rules as IDS mode but uses `drop` action instead of `alert`. Suricata sends TCP RST to the attacking source, actively blocking the connection.

### local.rules.vuln — Passive Mode

Only safelist pass rules — no detection rules active. Suricata becomes invisible to the attacker.

### local.rules.custom — Custom Rules

Empty placeholder for user-defined rules. Edit and Suricata picks up changes on next live reload.

## Safelist Rules

```
pass ip 172.18.0.100 any <> any any (msg:"SAFELIST — Security Auditor"; sid:9900001;)
pass ip 172.18.0.25 any <> any any (msg:"SAFELIST — Node-RED"; sid:9900002;)
pass ip 172.18.0.10 any <> any any (msg:"SAFELIST — Promtail"; sid:9900003;)
```

Prevents legitimate internal traffic from triggering alerts.

## Why network_mode: service:mosquitto

Suricata shares the broker's network stack — it sees all traffic entering and leaving the MQTT broker on all interfaces. This is more effective than:

- **Promiscuous mode on a separate interface** — requires a network tap or port mirroring
- **Listening on docker bridge** — may miss traffic depending on Docker networking mode

The trade-off: Suricata has no separate IP address and cannot be reached independently.

## MQTT App-Layer Inspection

```
app-layer:
  protocols:
    mqtt:
      enabled: yes
```

Enables Suricata's MQTT protocol parser, allowing deep inspection of MQTT payloads (subscribe topics, publish data) rather than just raw TCP patterns.

## Data Flow

```
Traffic → Mosquitto interface → Suricata (shared netns)
  → Detection match → eve.json
    → Promtail (shares suricata_logs volume) → Loki → Grafana SOC Dashboard
```

## Mode Switching (Node-RED)

Node-RED execs into Suricata container via Docker API proxy:
1. Replace `/etc/suricata/rules/local.rules` with desired rule file
2. Send `SIGUSR1` or `SIGUSR2` to reload rules
3. Alternatively: rewrite the file and Suricata picks up changes on next live reload

## Related

- Alert visualization: [10-grafana-dashboards.md](10-grafana-dashboards.md)
- Log pipeline: [09-observability-stack.md](09-observability-stack.md)
- IPS toggle in Node-RED: [03-nodered-automation.md](03-nodered-automation.md)
- Rule files: `infrastructure/suricata/local.rules.ids`, `.ips`, `.vuln`
