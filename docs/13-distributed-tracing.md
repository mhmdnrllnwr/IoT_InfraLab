# Distributed Tracing (OpenTelemetry + Tempo)

## Purpose

End-to-end distributed tracing across the IoT pipeline — from sensor telemetry generation through MQTT publish to security audit cycles. Enables visualization of request flow and performance bottlenecks in Grafana.

## Architecture

```
Sensor Node / Security Auditor
  → OTLP gRPC (4317)
    → OTEL Collector (batch processor)
      → otlp/tempo exporter
        → Tempo (storage)
          → Grafana Explore (Tempo datasource)
```

## Components

### Telemetry Producers

| Source | Service Name | Span Created |
|--------|-------------|--------------|
| docker_sensor | `iot-sensor-node-{id}` | `mqtt_publish_{topic}` |
| security-auditor | `security-auditor` | `audit_cycle` (root), `nmap_scan`, `ai_analysis`, `publish_report` |

### OTEL Collector

**Image:** `otel/opentelemetry-collector:latest`
**Container:** `otel_collector`
**Ports:** 4317 (gRPC), 4318 (HTTP)

**Pipeline:**
```
receivers: [otlp]
processors:
  batch:
    timeout: 5s
    send_batch_size: 10
exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  debug:
    verbosity: detailed
```

**Why a collector intermediary:**
- Decouples trace producers from trace storage — producers don't need to know about Tempo
- Enables pipeline transformation (batching, filtering, sampling) without client changes
- Single point for configuration changes

### Tempo

**Image:** `grafana/tempo:latest`
**Container:** `tempo`
**Memory:** 256 MB limit / 128 MB reserved

- OTLP receiver on gRPC 4317 and HTTP 4318
- Local filesystem storage at `/tmp/tempo/blocks`
- WAL at `/tmp/tempo/wal`

## Trace Details

### Sensor Publish Trace
```
Span: mqtt_publish_sensors/factory/{sensor_id}
  Attributes:
    - sensor_id: string
    - sensor_type: string  
    - profile: string
    - topic: string
```

### Security Auditor Trace
```
Span: audit_cycle (root)
  Attributes:
    - target_subnet: "172.18.0.0/24"
    - model: "gemini-2.0-flash"
  Children:
    - nmap_scan
    - ai_analysis
    - publish_report
```

## Querying Traces

In Grafana Explore, select **Tempo** datasource:

- Query by service: `{service.name="security-auditor"}`
- Query by sensor: `{service.name="iot-sensor-node-*"}`
- View span details: click individual spans for attributes, timing, and service mapping

## Security Note

All OTLP communication is plaintext (no TLS). This is acceptable in the lab environment but should use TLS in any deployment where trace data passes untrusted networks.

## Related

- OTEL collector config: `infrastructure/otel/otel-config.yaml`
- Tempo config: `infrastructure/tempo/tempo-config.yaml`
- Sensor OTEL instrumentation: [05-sensor-simulation.md](05-sensor-simulation.md)
- Auditor OTEL instrumentation: [07-security-auditor.md](07-security-auditor.md)
