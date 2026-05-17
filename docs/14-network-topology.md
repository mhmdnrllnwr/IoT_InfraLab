# Network Topology

## Purpose

Dedicated Docker bridge network for all inter-service communication. Isolates the lab environment from other Docker networks and the host.

## Network Configuration

```
Name: iot_infralab_net
Driver: bridge
Subnet: 172.18.0.0/24
Host Interface: br-iotlab
```

Defined in `docker-compose.yaml`:

```yaml
networks:
  iot_infralab_net:
    name: iot_infralab_net
    driver: bridge
    ipam:
      config:
        - subnet: 172.18.0.0/24
    driver_opts:
      com.docker.network.bridge.name: br-iotlab
```

## IP Assignment

### Static IPs

| Service | IP Address |
|---------|-----------|
| Node-RED | `172.18.0.25` |
| Promtail | `172.18.0.10` |
| Security Auditor | `172.18.0.100` |

### DHCP (auto-assigned)

| Service | Typical Range |
|---------|--------------|
| Mosquitto | `172.18.0.2` - `172.18.0.9` |
| Docker Proxy | `172.18.0.2` - `172.18.0.9` |
| InfluxDB | `172.18.0.2` - `172.18.0.9` |
| Grafana | `172.18.0.2` - `172.18.0.9` |
| Loki | `172.18.0.2` - `172.18.0.9` |
| Tempo | `172.18.0.2` - `172.18.0.9` |
| OTEL Collector | `172.18.0.2` - `172.18.0.9` |
| Telegraf | `172.18.0.2` - `172.18.0.9` |

### Special Cases

| Service | Assignment | Reason |
|---------|-----------|--------|
| Suricata | Shares Mosquitto's netns | `network_mode: service:mosquitto` — no separate IP |
| Sensors (dynamic) | DHCP via Docker API | Created at runtime by Node-RED |
| Attacker (dynamic) | DHCP via Docker API | Created during killchain simulation |

## Port Exposures (to Host)

| Host Port | Service | Purpose |
|-----------|---------|---------|
| 1883 | Mosquitto | MQTT |
| 9001 | Mosquitto | MQTT WebSocket |
| 1880 | Node-RED | UI + Dashboard |
| 3000 | Grafana | Dashboards |
| 8086 | InfluxDB | API (internal queries) |
| 3100 | Loki | Log queries |
| 4317 | OTEL Collector | OTLP gRPC |
| 4318 | OTEL Collector | OTLP HTTP |

All other services are internal-only with no host port mapping.

## Network Security

- **Isolated bridge** — services cannot access host network or other Docker networks by default
- **No external access** for Docker proxy, Tempo, Telegraf, Promtail — communication internal only
- **Dynamic containers** (sensors, attacker) are connected programmatically by Node-RED via Docker API
- **Container isolation (NAC)** — Node-RED can disconnect suspicious containers from the network via Docker API

## Related

- Full service list: [01-architecture-overview.md](01-architecture-overview.md)
- Suricata network mode: [08-suricata-ids-ips.md](08-suricata-ids-ips.md)
- Security model: [15-security-model.md](15-security-model.md)
