# IoT InfraLab — Testing & Verification Report

## Overview

This document catalogs all testing artifacts, methodologies, and results for the IoT InfraLab system. Testing is organized into four layers: **Unit**, **Integration**, **System/Benchmark**, and **Acceptance**.

---

## Layer 1: Unit Tests

**Framework:** pytest 9.0.3 with pytest-mock 3.15.1 and pytest-cov 7.1.0  
**Location:** `test/unit/`  
**Total tests:** 147  
**Run command:** `python -m pytest test/unit/ -v`  
**Requires:** `.venv` with dependencies installed (`pip install -r requirements-test.txt`). Auditor tests need `google-genai` package.

### test_simulator.py (34 tests)

| Category | Tests | What it validates |
|----------|-------|-------------------|
| Normal profile | 4 | Values within range, float type, variance across samples, type-specific ranges |
| Normal edge cases | 4 | Missing types default to [0,100], zero-width ranges return exact value, tuple ranges, negative ranges |
| Failing profile | 5 | No drift at t=0, monotonic drift over time, drift formula (5%/30s), values at 30s/60s, large elapsed |
| Erratic profile | 3 | Base values in range, ~10% spike rate, 2-4x spike multiplier |
| Vibration precision | 2 | Vibration = 3 decimal places, temperature = 1 decimal |
| Blueprint overrides | 3 | Blueprint range overrides base, scoped per type, missing range key falls back |
| load_config() | 7 | Loads types/blueprints, missing files, malformed JSON, sensor overrides, reload clears state |
| Config+Value integration | 2 | Config feeds value generation, blueprint affects value range |
| Module constants | 4 | MQTT_BROKER, OTLP_ENDPOINT, INTERVAL type, topic format |

**Result:** 34/34 passed

### test_benchmark_utils.py (48 tests)

| Category | Tests | What it validates |
|----------|-------|-------------------|
| Timer | 6 | Positive elapsed, matches sleep duration, context manager syntax, elapsed_sec property, zero-case, reuse |
| parse_memory_mb | 10 | MiB/GiB/KiB/MB/GB/B units, empty string, None, malformed, no unit |
| parse_cpu_percent | 4 | Standard % strings, empty, no % sign |
| validate_sensor_payload | 8 | Valid payload, missing fields, wrong types, None, non-dict, extra fields |
| Bench naming | 12 | bench_name() for all cmd combos, is_bench_container() for edge cases |

**Result:** 48/48 passed

### test_dashboards.py (30 tests)

| Category | Tests | What it validates |
|----------|-------|-------------------|
| create_base() | 9 | Dict structure, required keys, title/uid/tags, empty panels, schema version |
| IoT Sensors | 6 | Panels exist, required keys per panel, known types, Flux queries |
| Platform Health | 5 | Panels, keys, known types, templating vars, Docker query presence |
| Security SOC | 6 | Panels, keys, known types (including piechart/bargauge/logs), Loki queries |
| Output | 4 | JSON serializable, roundtrip re-parse |

**Result:** 30/30 passed

### test_attacker.py (16 tests)

| Module | Tests | What it validates |
|--------|-------|-------------------|
| mqtt_inject | 7 | Default/custom port, broker required, default/custom topic/value |
| mqtt_sniff | 5 | Broker required, default/custom port, default/custom timeout |
| mqtt_dos | 4 | Broker required, default/custom port, default/custom threads |

**Result:** 16/16 passed

### test_auditor.py (17 tests)

| Category | Tests | What it validates |
|----------|-------|-------------------|
| on_message | 6 | Model change, status publish, scan thread trigger, cooldown gate, scanning lock, irrelevant topic |
| perform_audit | 7 | Empty scan, AI success path, nmap error, AI 429/503 quota, scanning flag reset |
| Module constants | 5 | BROKER, TARGET_SUBNET, COOLDOWN_TIME, MODEL_ID, client_mqtt |

**Notes:** Uses extensive mocking (nmap.PortScanner, genai.Client, mqtt.Client, OTel BatchSpanProcessor). No real MQTT broker, Gemini API, or network scan required. OTel background export errors are non-fatal (collector is Docker-internal).

**Auditor refactoring:** `auditor.py` main loop was moved into `if __name__` to make the module importable. Attacker scripts (`mqtt_inject.py`, `mqtt_sniff.py`, `mqtt_dos.py`) had their argparse parsers moved to module level for testability.

**Result:** 17/17 passed

### Unit Test Summary

| Test file | Tests | Pass | Fail | Coverage target |
|-----------|-------|------|------|-----------------|
| test_simulator.py | 34 | 34 | 0 | sensor value generation, config loading |
| test_benchmark_utils.py | 48 | 48 | 0 | Timer, parse utilities, validation |
| test_dashboards.py | 30 | 30 | 0 | dashboard structure, panel schemas |
| test_attacker.py | 16 | 16 | 0 | argparse configuration |
| test_auditor.py | 17 | 17 | 0 | audit logic, MQTT handlers, constants |
| **Total** | **147** | **147** | **0** | |

---

## Layer 2: Integration Tests

### Smoke Test

**File:** `test/smoke_test.py`  
**Run command:** `python test/smoke_test.py`  
**Requires:** Stack running (`docker compose up -d`)

| # | Check | What It Validates | Method |
|---|-------|-------------------|--------|
| 1 | MQTT Broker | Mosquitto reachable on port 1883 | TCP socket connect |
| 2 | InfluxDB | HTTP 200 on `/health` | HTTP GET |
| 3 | Grafana | HTTP 200 on `/api/health` | HTTP GET |
| 4 | Node-RED | HTTP 200 on `/` | HTTP GET |
| 5 | Data Pipeline | MQTT publish/consume round trip | paho-mqtt publish + subscribe |

**Expected output:**
```
[1/5] MQTT Broker ......... OK
[2/5] InfluxDB ............ OK
[3/5] Grafana ............. OK
[4/5] Node-RED ............ OK
[5/5] Data Pipeline ....... OK (or WARN — depends on echo subscriber)
```

### Docker Compose Validation

**Command:** `docker compose config`  
**What:** Validates compose file syntax, resolves env vars. Exit 0 = valid.

### Build Verification

**Command:** `docker compose build <service>`  
**What:** Builds container images, verifies Dockerfiles. Run after any Dockerfile change.

### File-level Syntax Checks

| File type | Command |
|-----------|---------|
| Python | `python -m py_compile file.py` |
| YAML | Manual structure review (2-space indent, valid keys) |
| JSON | `python -m json.tool file.json` |

---

## Layer 3: System / Benchmark Tests

### Sensor Deployment Benchmark

**File:** `test/benchmark_sensors.py` (1,888 lines)  
**Run command:** `python test/benchmark_sensors.py <subcommand>`  
**Requires:** Stack running, `iot-sensor` image built

| Subcommand | What It Measures | Key Metrics |
|------------|-----------------|-------------|
| `health` | Pre-flight checks (7 checks) | Docker, image, network, MQTT, InfluxDB, Grafana, Node-RED |
| `startup` | Cold-start timing per service | `docker compose up -d` wall time, per-service readiness |
| `deploy --count N` | Sensor deployment lifecycle | create/start/mqtt times, total lifecycle |
| `scale --max N --step S` | Scaling curve | Memory/cpu per sensor at each load level |
| `latency` | MQTT latency at multiple loads | p50/p95/p99, delivery rate, throughput |
| `resources --sensors N` | Idle vs loaded comparison | Platform memory, per-sensor footprint |
| `all` | Full suite | All benchmarks sequentially |
| `report` | JSON→CSV export | Re-export saved results |

**Output:** JSON report in `test/reports/`, CSVs per category

### Benchmark Results (Baseline)

**Environment:** Docker Desktop (Windows 11), 12 vCPUs, 3.6 GB RAM, Docker Engine 29.4.2

| Metric | Value |
|--------|-------|
| Sensor deployment lifecycle (mean) | 1,846 ms |
| Time to first MQTT message (mean) | 673 ms |
| Per-sensor memory | ~25 MB |
| Per-sensor CPU | ~0.3% |
| Scaling formula | `MB = 25.5 × N` |
| Theoretical max sensors (RAM) | ~94 |
| Idle platform memory (12 services) | 1,212 MB |
| 5-sensor memory delta | +87 MB |
| MQTT p95 latency | ~450 ms (first-message dominant) |
| Stack ready time | ~16s (Loki ingress warmup) |

### Sensor Limit Test

**Files:** `test/sensor-limit-test.md`, `test/sensor_ramp_test.ps1`, `test/sensor_ramp_test.sh`  
**Method:** Batch creates in groups of 10 with `--memory=64m`, monitors until failure

| Load Level | Status | Bottleneck |
|------------|--------|------------|
| 0-40 sensors | Healthy | No issues detected |
| 40-50 sensors | Degraded | InfluxDB write pressure rising |
| 50-60 sensors | Stressed | InfluxDB CPU 67-87% |
| ~64 sensors | **Crash** | Docker Desktop WSL2 VM OOM |

**Key constraints:**
- **Safe operational limit:** 40-50 sensors
- **Hard limit:** ~64 sensors (Docker WSL2 VM memory exhaustion)
- **MQTT is not the bottleneck** — Mosquitto used 2.4 MB at 60 sensors
- **Network:** /24 subnet (254 IPs) is not a constraint

### Full Benchmark Report

**File:** `test/BENCHMARK_RESULTS.md`  
Contains detailed results with per-service startup timing, per-sensor lifecycle data, scaling curve formulas, MQTT latency distributions, and per-service resource breakdown.

---

## Layer 4: Acceptance Tests

**File:** `test/test_acceptance.py` (~700 lines)  
**Run command:** `python test/test_acceptance.py` (full suite)  
**Criteria document:** `test/ACCEPTANCE_CRITERIA.md`  
**Requires:** Stack running with all 12 containers

### Scenarios

| ID | Scenario | Tests | What It Validates |
|----|----------|-------|-------------------|
| A | Stack Health | 10 | Docker reachable, all containers running, ports respond, MQTT works, image exists, network exists |
| B | Sensor Lifecycle | 7 | Create + start sensor, MQTT message within 10s, valid payload structure, InfluxDB within 30s, cleanup |
| C | Data Pipeline | 6 | Grafana datasources (Loki, Tempo, InfluxDB), dashboards provisioned, InfluxDB buckets, Promtail→Loki logs, OTel port |
| D | Security Audit | 5 | Container running, SCAN_NOW triggers report, HTML table in report, status updates (requires Gemini API key) |
| E | Suricata Detection | 3 | Container running, eve.json exists with alerts, scan triggers detection |
| F | Attack Simulation | 3 | MQTT inject publish, wildcard subscribe, anonymous publish |
| G | Cleanup | 3 | Remove stale sensors, no bench_* orphans, compose validation |

### Acceptance Test Results

**Last run:** 2026-05-19  
**Total:** 29/29 passed (scenarios A, B, C, F, G)

| Scenario | Passed | Failed | Notes |
|----------|--------|--------|-------|
| A — Stack Health | 10 | 0 | |
| B — Sensor Lifecycle | 7 | 0 | MQTT within ~2s, InfluxDB within 30s |
| C — Data Pipeline | 6 | 0 | Grafana auth reads from `.env` |
| F — Attack Simulation | 3 | 0 | |
| G — Cleanup | 3 | 0 | |
| D — Security Audit | — | — | Requires Gemini API key; run manually with `-s D` |
| E — Suricata Detection | — | — | Manual run with `-s E` |
| **Total** | **29** | **0** | |

### Usage

```powershell
# Full suite (quick scenarios)
python test/test_acceptance.py

# With security + suricata (Gemini API key required)
python test/test_acceptance.py -s A,B,C,D,E,F,G

# Single scenario
python test/test_acceptance.py -s B

# List available scenarios
python test/test_acceptance.py --list
```

---

## Complete Test Coverage Map

| Layer | Tests/Checks | Automation | Requires Stack | Requires API Key |
|-------|-------------|------------|----------------|-----------------|
| Unit | 147 pytest | Full | No | No |
| Integration | 5 checks + file validations | Script | Yes | No |
| System/Benchmark | 8 subcommands | Script | Yes | No |
| Acceptance | 29-36 checks | Script | Yes | Optional (D/E) |

### Files Reference

| File | Layer | Purpose |
|------|-------|---------|
| `test/unit/test_simulator.py` | Unit | Sensor value generation, profiles, config loading |
| `test/unit/test_benchmark_utils.py` | Unit | Timer, parse utilities, payload validation |
| `test/unit/test_dashboards.py` | Unit | Dashboard structure, panel schemas |
| `test/unit/test_attacker.py` | Unit | Attack script arg parsing |
| `test/unit/test_auditor.py` | Unit | Audit logic, MQTT handlers |
| `test/smoke_test.py` | Integration | Service reachability, MQTT pipeline |
| `test/benchmark_sensors.py` | System | Performance metrics, scaling, latency |
| `test/test_acceptance.py` | Acceptance | End-to-end pass/fail scenarios |
| `test/ACCEPTANCE_CRITERIA.md` | Acceptance | Human-readable pass/fail rubric |
| `test/BENCHMARK_RESULTS.md` | System | Detailed benchmark results |
| `test/sensor-limit-test.md` | System | Sensor limit test results |
| `test/reports/` | System | JSON reports + CSV exports |
| `docs/18-testing-verification.md` | All | This document |

### Running All Tests

```powershell
# 1. Unit tests (no stack required)
.venv\Scripts\pip install -r requirements-test.txt
python -m pytest test/unit/ -v

# 2. Integration smoke test
python test/smoke_test.py

# 3. Benchmarks (requires built sensor image)
python test/benchmark_sensors.py health
python test/benchmark_sensors.py startup --skip-down

# 4. Acceptance tests
python test/test_acceptance.py
```
