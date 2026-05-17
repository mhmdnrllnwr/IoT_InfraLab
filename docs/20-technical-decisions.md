# Technical Decisions

## Purpose

Complete reference of key technical decisions made during the design and implementation of IoT InfraLab. Each entry includes the chosen approach, the alternatives considered, and the rationale.

---

## Infrastructure & Orchestration

### Named Volumes vs Bind Mounts

| Factor | Named Volumes (chosen) | Bind Mounts |
|--------|----------------------|-------------|
| Persistence | Survives `docker compose down` | Survives container restart |
| Cleanup | Explicit `down -v` to remove | Manual directory removal |
| Performance | Managed by Docker driver | Host filesystem |

**Why chosen:** Data survives container lifecycle. `docker compose down` (without `-v`) preserves all data. Cleaner for stateful services (InfluxDB, Grafana, Loki).

---

### Single Compose File vs Multiple Files

| Factor | Single File (chosen) | Multiple Files |
|--------|---------------------|---------------|
| Management | One file, one command | Split by zone/function |
| Override complexity | None | Needs `-f` flags or `docker-compose.override.yml` |
| Learning curve | Lower | Higher |

**Why chosen:** Single `docker compose up -d` deploys everything. No confusing `-f` flags. Simpler for FYP scope and documentation.

---

### Docker Socket Proxy vs Direct Mount

| Factor | Socket Proxy (chosen) | Direct Socket Mount |
|--------|----------------------|-------------------|
| Security | Fine-grained API control | Root-equivalent access |
| Manageability | Environment flags | All-or-nothing |
| Complexity | One extra container | Simpler setup |

**Why chosen:** Allows Node-RED to manage containers without giving full Docker daemon access. Can selectively enable POST/DELETE/EXEC while blocking other API surfaces.

---

## MQTT & Messaging

### Mosquitto Anonymous vs Password Auth

| Factor | Anonymous (chosen for lab) | Password Auth |
|--------|---------------------------|---------------|
| Attack scenario realism | Enables sniffing/injection/DoS | Prevents MQTT attacks entirely |
| Setup complexity | Zero | Needs passwd + ACL files |
| IDS visibility | Plaintext inspection | TLS would blind Suricata |

**Why chosen:** Anonymous mode is the foundational vulnerability enabling the entire attack simulation. Hardened config exists for production use.

---

### Single Broker vs Multiple Brokers

**Chosen:** Single Mosquitto instance for all traffic.

**Rationale:** All services on one network, one broker simplifies the topology. Attack scenarios are clearer when all traffic passes through one observable point.

---

## Intrusion Detection

### Suricata in Mosquitto NetNS vs Separate Interface

| Factor | Shared NetNS (chosen) | Separate Interface |
|--------|----------------------|-------------------|
| Traffic visibility | Full (all broker traffic) | Requires port mirroring |
| IP management | No separate IP | Needs its own address |
| Complexity | Simple `network_mode` | Needs network tap config |

**Why chosen:** Suricata sees all traffic entering/leaving the MQTT broker. No second IP needed. Trade-off: cannot be reached independently.

---

### 3 Rule Sets vs Single Rule File

| Factor | 3 Rule Sets (chosen) | Single File |
|--------|---------------------|-------------|
| Runtime switching | Yes (Node-RED swap) | No |
| Mode clarity | Alert / Drop / Passive clearly separated | Mixed mode |
| Complexity | 3 files to maintain | One file |

**Why chosen:** Enables runtime IPS mode toggle from Node-RED dashboard without rebuilding or restarting Suricata.

---

### Suricata MQTT App-Layer vs Raw TCP Only

**Chosen:** MQTT app-layer parsing enabled.

**Rationale:** Deep inspection of MQTT subscribe topics and publish data. Detects `#` wildcard subscriptions via protocol-aware parsing (sid:1000005, though native parser commented out; fallback raw hex detection in sid:1000007).

---

## Observability

### OTEL Collector Intermediary vs Direct-to-Tempo

| Factor | Collector (chosen) | Direct-to-Tempo |
|--------|-------------------|-----------------|
| Decoupling | Producers don't know storage | Each producer configures Tempo |
| Pipeline transformation | Batching, sampling, filtering | None |
| Single config point | Yes | Changes require client updates |

**Why chosen:** Sensor and auditor containers send to `otel-collector:4317` regardless of backend. Batching improves performance. One config change adjusts the entire pipeline.

---

### Telegraf vs Prometheus for Metrics

| Factor | Telegraf (chosen) | Prometheus |
|--------|------------------|------------|
| Deployment | Single container | Server + exporters per target |
| InfluxDB output | Native | Requires adapter |
| Docker metrics | Built-in plugin | Requires cadvisor |
| Config | One TOML file | Multiple scrape configs |

**Why chosen:** Simpler setup for the lab scope. Single container, built-in Docker input, native InfluxDB output. Prometheus would add unnecessary complexity.

---

### InfluxDB 2.7 vs 3.x

| Factor | InfluxDB 2.7 (chosen) | InfluxDB 3.x |
|--------|----------------------|--------------|
| Stability | Mature, well-documented | Newer, fewer resources |
| Feature set | Sufficient for FYP | Additional features not needed |
| Migration path | Easy upgrade when needed | Requires schema changes |

**Why chosen:** Stable and sufficient for the lab's time-series needs. 3.x provides no material benefit for this use case.

---

### Loki Filesystem Storage vs S3/GCS

**Chosen:** Local filesystem storage (single-instance mode).

**Rationale:** Lab deployment with no need for distributed storage. Filesystem is simpler, requires no cloud dependencies. Named volume ensures data persistence.

---

## Simulation

### Python for Sensor/Attacker vs Go/Rust

| Factor | Python (chosen) | Go/Rust |
|--------|----------------|---------|
| Development speed | Fast | Slower |
| Performance | Sufficient (one publish per N seconds) | Overkill |
| Dependencies | paho-mqtt, opentelemetry | Would need native MQTT libs |
| Container size | ~200 MB (slim) | ~10-20 MB |

**Why chosen:** Sensor publishes at configurable intervals (typically 1-5s) — Python's performance is more than adequate. Faster iteration for FYP. OpenTelemetry SDK support is mature.

---

### Gemini AI (Cloud) vs Local LLM

| Factor | Gemini (chosen) | Local LLM (Ollama/Llama) |
|--------|----------------|-------------------------|
| GPU requirement | None | Required for reasonable speed |
| Setup complexity | API key only | Model download + container |
| Cost | Free tier sufficient (for FYP) | Free but uses local resources |
| API quality | Production-grade | Variable |

**Why chosen:** Zero GPU requirement, simple API integration (one Python library), free tier sufficient for FYP. Local LLM would require significant GPU resources on the development machine.

---

### 3 Sensor Profiles vs Continuous Range

**Chosen:** Three discrete behavior profiles (normal, failing, erratic).

**Rationale:** Clear categories for dashboard anomaly detection panels. Each profile produces visually distinct patterns — easier to demonstrate IDS/alerting in an educational context. Continuous parameter space would be more realistic but harder to demo.

---

## UI & Automation

### Node-RED vs Custom Dashboard

| Factor | Node-RED (chosen) | Custom (React/Flask) |
|--------|------------------|---------------------|
| Development speed | Visual flow programming | Full-stack development |
| MQTT integration | Built-in subscribe/publish | Needs library |
| Docker API integration | HTTP Request nodes | Needs Docker SDK |
| Dashboard UI | Dashboard 2.0 framework | Build from scratch |
| Learning curve | Visual, intuitive | Code-only |

**Why chosen:** Node-RED provides MQTT, Docker API, and InfluxDB integration out of the box. Dashboard 2.0 gives a professional UI without frontend development. For a simulation lab, visual flow programming makes the architecture transparent.

---

### Dashboard Dashboard 2.0 vs UI Builder

**Chosen:** `@flowfuse/node-red-dashboard` (Dashboard 2.0).

**Rationale:** Modern, maintained, supports theming and complex layouts. Earlier UI Builder versions had limited widget sets.

---

### Grafana YAML Provisioning vs Manual Import

**Chosen:** Auto-provisioning via YAML provider config.

**Rationale:** Dashboards auto-load on Grafana startup. Reproducible across environments. Version-controlled JSON files in `infrastructure/grafana/provisioning/dashboards/`.

---

### Generated Dashboards vs Hand-written JSON

| Factor | Generated (chosen) | Hand-written |
|--------|-------------------|--------------|
| Consistency | Shared templates | Manual duplication |
| Updates | Edit once, regenerate | Edit 3 files |
| Diff clarity | Python changes readable | JSON diffs noisy |

**Why chosen:** `gen_dashboards.py` uses shared panel templates. Adding a panel to all dashboards is a one-line addition to a list. Hand-written JSON would require copying panel definitions to each file.

---

## Summary

| Category | Decision | Primary Reason |
|----------|----------|---------------|
| Orchestration | Single compose file | Simplicity |
| Storage | Named Docker volumes | Data persistence |
| MQTT | Mosquitto, anonymous | Enable attack scenarios |
| IDS | Suricata in broker netNS | Full traffic visibility |
| IDS rules | 3 rule sets | Runtime mode switching |
| Metrics | Telegraf | Single container, native InfluxDB |
| Traces | OTEL Collector intermediary | Decoupling, pipeline flexibility |
| DB | InfluxDB 2.7 | Stable, sufficient |
| Simulation | Python | Fast iteration, FYP scope |
| AI | Gemini (cloud) | Zero GPU, simple API |
| UI | Node-RED Dashboard 2.0 | Visual flow, built-in integrations |
| Dashboards | YAML-provisioned, Python-generated | Reproducibility, consistency |

## Related

- Architecture: [01-architecture-overview.md](01-architecture-overview.md)
- Security model: [15-security-model.md](15-security-model.md)
