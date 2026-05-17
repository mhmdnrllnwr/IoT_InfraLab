# Shutdown & Lessons Learned

## Purpose

Final documentation report covering manual testing results, general observations, unexpected challenges during development, lessons learned, and recommendations for future work. This file differs from others — it captures subjective experience and retrospective analysis rather than technical reference.

> **Note:** This file serves as the concluding chapter of the FYP report. The user should fill it out based on their hands-on experience with the lab.

---

## Manual Testing Results

### Test 1: Full Stack Deployment

| Step | Expected | Actual | Timestamp |
|------|----------|--------|-----------|
| `docker compose up -d` | All 12 containers start | ... | ... |
| Containers healthy | All show "Up" in `docker compose ps` | ... | ... |
| Smoke test passes | 5/5 checks OK | ... | ... |

### Test 2: Sensor Lifecycle

| Step | Expected | Actual |
|------|----------|--------|
| Create sensor via Node-RED | Container appears in Docker | ... |
| Deploy sensor | Container starts, connects to network | ... |
| Monitor telemetry | Live data in dashboard feed | ... |
| Kill sensor | Container stops, feed stops | ... |

### Test 3: Attack Simulation

| Phase | Expected | Actual |
|-------|----------|--------|
| Create Attacker | Attacker container appears | ... |
| Breach Network | Container on `iot_infralab_net` | ... |
| Nmap Scan | Open ports discovered | ... |
| Sniff MQTT | Telemetry captured | ... |
| SYN Flood | Broker connection saturated | ... |
| Suricata Alert | Alert appears in Grafana SOC Dashboard | ... |
| IPS Mode | Attack blocked (TCP RST) | ... |

### Test 4: AI Security Audit

| Step | Expected | Actual |
|------|----------|--------|
| Trigger scan | Auditor starts nmap | ... |
| Gemini analysis | HTML report returned | ... |
| Report in dashboard | Scan results visible in Node-RED | ... |

### Test 5: Observability

| Check | Expected | Actual |
|-------|----------|--------|
| InfluxDB has data | Query returns sensor points | ... |
| Loki has alerts | Suricata alerts queryable | ... |
| Tempo shows traces | Trace spans visible in Grafana Explore | ... |
| Grafana dashboards render | All 3 dashboards show panels with data | ... |

---

## General Observations

*What stood out during development and testing. Fill in based on experience.*

- ...
- ...

---

## Unexpected Challenges

| Challenge | Context | How It Was Resolved |
|-----------|---------|-------------------|
| Checksum validation | Suricata under WSL2 | Set `stream.checksum-validation: no` |
| ... | ... | ... |

---

## Lessons Learned

*Key takeaways from building this system. Fill in.*

1. ...
2. ...
3. ...

---

## Future Work / Recommendations

1. **Kubernetes deployment** — migrate from Docker Compose to K3s/K8s for production-like orchestration
2. **Additional IDS rules** — expand Suricata ruleset for more attack scenarios (DNS tunneling, ARP spoofing)
3. **Machine learning detection** — replace heuristic anomaly detection with ML model trained on sensor profiles
4. **Real hardware integration** — connect physical IoT sensors via ESP32/Raspberry Pi
5. **SIEM integration** — forward alerts to Wazuh or Elastic SIEM for correlation
6. **TLS implementation** — add mutual TLS for MQTT, evaluate impact on IDS visibility
7. **Automated red teaming** — script full killchain with randomized parameters
8. **Performance benchmarking** — measure throughput limits per component (MQTT msgs/sec, Suricata pps, Loki ingest)
9. **Multi-node deployment** — distribute services across multiple hosts with Docker Swarm
10. **Compliance mapping** — map attack scenarios to MITRE ATT&CK framework tactics

---

## Appendix: Test Outputs

### Smoke Test

```
python test/smoke_test.py

Expected:
[1/5] MQTT Broker ......... OK
[2/5] InfluxDB ............ OK
[3/5] Grafana ............. OK
[4/5] Node-RED ............ OK
[5/5] Data Pipeline ....... OK
```

*Paste actual output here after testing.*

### Docker Compose PS

```
docker compose ps

Expected: 12 services all "Up"
```

*Paste actual output here.*

---

## Related

- Deployment guide: [19-deployment-guide.md](19-deployment-guide.md)
- Testing: [18-testing-verification.md](18-testing-verification.md)
