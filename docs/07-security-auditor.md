# Security Auditor

## Purpose

AI-powered vulnerability scanner that performs automated network reconnaissance and generates security recommendations using Google Gemini. Triggered from Node-RED Security Ops dashboard.

## Container

**Image:** Built from `src/simulation/auditor_security/Dockerfile`
**Base:** `python:3.11-alpine`
**IP:** `172.18.0.100` (static)
**Memory:** 128 MB

### Dependencies

- `paho-mqtt` — MQTT communication
- `google-genai` — Gemini API client
- `python-nmap` — Programmatic port scanning
- `opentelemetry-api` + `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-grpc` — distributed tracing
- `nmap` (apk package) — network scanner binary

## Architecture

### MQTT Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `lab/security/trigger` | Node-RED → Auditor | `SCAN_NOW` |
| `lab/security/model` | Node-RED → Auditor | Model name (e.g., `gemini-2.0-flash`) |
| `lab/security/report` | Auditor → Node-RED | HTML table of scan results |
| `lab/security/status` | Auditor → Node-RED | Status heartbeat |

### Audit Cycle Flow

```
1. Subscribe lab/security/trigger, lab/security/model
2. Receive SCAN_NOW → spawn daemon thread
3. Create OTEL span "audit_cycle" (attributes: target_subnet, model)
4. Sub-span: Nmap scan
   → nmap.PortScanner().scan('172.18.0.0/24', arguments='-sT -T4')
5. Sub-span: AI analysis
   → Send structured scan data to Gemini 2.0 Flash
   → Prompt requires HTML <table> response:
     columns: Target Host, Service, Risk Analysis, Security Recommendation
6. Sub-span: Publish report
   → Publish AI response to lab/security/report
```

### Rate Limiting

- **Cooldown:** 30 seconds between scans
- **Errors:** Handles 429 (retry-after), 503 (degraded mode), missing API key (skips AI, returns raw scan)

## AI Prompt Design

The Gemini prompt enforces structured output:
- Must return valid HTML `<table>`
- Columns: Target Host, Service, Risk Analysis, Security Recommendation
- No markdown, no extra commentary — parseable HTML only
- Scans all discovered hosts and open ports from the nmap result

## Distributed Tracing

Each audit cycle produces a trace:
```
audit_cycle (root span)
  ├── nmap_scan (sub-span)
  ├── ai_analysis (sub-span)
  └── publish_report (sub-span)
```

View in Grafana: Explore → Tempo → `{service.name="security-auditor"}`

## Related

- Trace visualization: [13-distributed-tracing.md](13-distributed-tracing.md)
- Triggering scans: [03-nodered-automation.md](03-nodered-automation.md)
