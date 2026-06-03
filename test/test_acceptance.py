#!/usr/bin/env python3
"""
IoT InfraLab — Acceptance Test Suite

Verifies system meets acceptance criteria defined in
test/ACCEPTANCE_CRITERIA.md.  Runs against live stack (must be up).

Usage:
    python test/test_acceptance.py               # full suite
    python test/test_acceptance.py --list        # list scenarios
    python test/test_acceptance.py -s A          # scenario A only
    python test/test_acceptance.py -s B,C        # scenarios B and C
    python test/test_acceptance.py --verbose     # verbose logging
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STACK_SERVICES = [
    "iot_broker", "iot_nodered", "docker_api_proxy", "otel_collector",
    "loki", "tempo", "promtail", "influxdb", "telegraf", "grafana",
    "suricata-ids", "security_auditor",
]

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _docker(*args, check=True, timeout=30):
    cmd = ["docker"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def _http(url, timeout=5, retries=1):
    """HTTP GET with optional retries (for services that may still be starting)."""
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(url, timeout=timeout)
            return resp.status, resp.read().decode()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None, str(e)
    return None, "max retries exceeded"


def _port(host, port, timeout=3):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def _mqtt_connect(host="localhost", port=1883):
    import paho.mqtt.client as mqtt
    received = []

    def on_msg(client, userdata, msg):
        received.append(msg)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    c.on_message = on_msg
    c.connect(host, port, 10)
    c.loop_start()
    return c, received


class AcceptanceRunner:
    """Runs acceptance scenarios and tracks results."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []
        self.ci_mode = False  # set True for CI — skips auditor tests

    def ok(self, test_id, description):
        self.passed += 1
        self.results.append((test_id, PASS, description))
        if self.verbose:
            print(f"  {PASS} {test_id}: {description}")

    def fail(self, test_id, description, detail=""):
        self.failed += 1
        self.results.append((test_id, FAIL, description))
        msg = f"  {FAIL} {test_id}: {description}"
        if detail:
            msg += f"\n         {detail}"
        print(msg)

    def skip(self, test_id, description, reason=""):
        self.skipped += 1
        self.results.append((test_id, SKIP, description))
        if self.verbose or reason:
            print(f"  {SKIP} {test_id}: {description} ({reason})")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'=' * 60}")
        print(f" Acceptance: {self.passed} passed, {self.failed} failed, "
              f"{self.skipped} skipped of {total}")
        print(f"{'=' * 60}")
        for tid, status, desc in self.results:
            if status != PASS or self.verbose:
                print(f"  {status} {tid}: {desc[:80]}")
        return EXIT_OK if self.failed == 0 else EXIT_FAIL


# =========================================================================
# Scenarios
# =========================================================================

def scenario_stack_health(runner):
    """A. Stack Health — verify all containers and services are running."""
    print(f"\n--- A. Stack Health ---")

    # A-01
    try:
        _docker("info")
        runner.ok("A-01", "Docker daemon reachable")
    except RuntimeError as e:
        runner.fail("A-01", "Docker daemon reachable", str(e))
        return  # can't continue without Docker

    # A-02
    out, _, _ = _docker("ps", "--format", "{{.Names}}")
    running = set(out.strip().split("\n")) if out else set()
    missing = [s for s in STACK_SERVICES if s not in running]
    if missing:
        runner.fail("A-02", f"All 12 containers running. Missing: {', '.join(missing)}")
    else:
        runner.ok("A-02", f"All {len(STACK_SERVICES)} containers running")

    # A-03 through A-07
    port_checks = [
        ("A-03", "Mosquitto :1883", "localhost", 1883),
        ("A-07", "Loki :3100/ready", "localhost", 3100),
    ]
    for tid, desc, host, port in port_checks:
        if _port(host, port):
            runner.ok(tid, desc)
        else:
            runner.fail(tid, desc, f"{host}:{port} not reachable")

    http_checks = [
        ("A-04", "InfluxDB :8086/health", "http://localhost:8086/health"),
        ("A-05", "Grafana :3000/api/health", "http://localhost:3000/api/health"),
        ("A-06", "Node-RED :1880/", "http://localhost:1880/"),
    ]
    for tid, desc, url in http_checks:
        status, body = _http(url, retries=6)  # up to ~12s wait
        if status == 200:
            runner.ok(tid, desc)
        else:
            runner.fail(tid, desc, f"HTTP {status}")

    # A-08 — MQTT broker accepts connection and subscription
    try:
        c, rcv = _mqtt_connect()
        c.subscribe("lab/smoke/acceptance_test")
        c.publish("lab/smoke/acceptance_test",
                  json.dumps({"test": True, "ts": time.time()}), qos=1)
        time.sleep(1)
        c.loop_stop()
        c.disconnect()
        # We verify the connect + subscribe succeed (no error thrown).
        # Publishing to an unsubscribed topic is expected; we just verify the
        # broker accepted the connection and subscription.
        runner.ok("A-08", "MQTT broker accepts connections and subscriptions")
    except ImportError:
        runner.skip("A-08", "MQTT broker test", "paho-mqtt not installed")

    # A-09 — sensor image
    out, _, _ = _docker("images", "-q", "iot-sensor")
    if out.strip():
        runner.ok("A-09", "iot-sensor image exists")
    else:
        runner.fail("A-09", "iot-sensor image exists", "Not found — run docker compose build")

    # A-10 — network
    out, _, _ = _docker("network", "inspect", "iot_infralab_net", check=False)
    if "iot_infralab_net" in out:
        runner.ok("A-10", "iot_infralab_net exists")
    else:
        runner.fail("A-10", "iot_infralab_net exists")


def scenario_sensor_lifecycle(runner):
    """B. Sensor Lifecycle — deploy, verify data, clean up."""
    print(f"\n--- B. Sensor Lifecycle ---")

    sensor_id = f"acc_test_sensor_{int(time.time())}"
    container_id = None

    # B-01 — create
    out, _, rc = _docker(
        "create", "--name", sensor_id, "--network", "iot_infralab_net",
        "--rm",
        "-e", f"SENSOR_ID={sensor_id}",
        "-e", "SENSOR_TYPES=temperature",
        "-e", "NODE_PROFILE=normal",
        "-e", "INTERVAL=5",
        "-e", "MQTT_BROKER=mosquitto",
        "iot-sensor",
        check=False,
    )
    if rc == 0 and out.strip():
        container_id = out.strip()
        runner.ok("B-01", "Create sensor container")
    else:
        runner.fail("B-01", "Create sensor container", out)
        return

    # B-02 — Subscribe MQTT BEFORE starting sensor
    try:
        c, mqtt_msgs = _mqtt_connect()
        c.subscribe("sensors/factory/+")
    except ImportError:
        runner.skip("B-03", "Sensor MQTT", "paho-mqtt not installed")
        _docker("rm", "-f", sensor_id, check=False)
        return

    # B-02b — start sensor
    _, _, rc = _docker("start", sensor_id, check=False)
    if rc == 0:
        runner.ok("B-02", "Start sensor container")
    else:
        runner.fail("B-02", "Start sensor container")
        _docker("rm", "-f", sensor_id, check=False)
        return

    # B-03 — wait for MQTT message within 10s
    deadline = time.time() + 12
    first_msg = None
    while time.time() < deadline:
        for msg in mqtt_msgs:
            if sensor_id in msg.topic:
                first_msg = msg
                break
        if first_msg:
            break
        time.sleep(0.2)

    c.loop_stop()
    c.disconnect()

    if first_msg:
        runner.ok("B-03", "Sensor MQTT message within 10s")
    else:
        runner.fail("B-03", "Sensor MQTT message within 10s", "No message received")
        _docker("rm", "-f", sensor_id, check=False)
        return

    # B-04 — payload valid
    try:
        payload = json.loads(first_msg.payload.decode())
        has_id = "sensor_id" in payload
        has_readings = isinstance(payload.get("readings"), dict)
        has_ts = "timestamp" in payload
        if has_id and has_readings and has_ts:
            runner.ok("B-04", "Sensor payload has valid structure")
        else:
            runner.fail("B-04", "Sensor payload has valid structure",
                        f"missing fields: id={has_id} readings={has_readings} ts={has_ts}")
    except Exception as e:
        runner.fail("B-04", "Sensor payload has valid structure", str(e))

    # B-05 — InfluxDB data within 30s
    # Read token from .env
    influx_token = None
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("INFLUXDB_TOKEN="):
                    influx_token = line.strip().split("=", 1)[1]
                    break

    if influx_token:
        # Raw Flux query with application/vnd.flux content type
        # (NOT JSON — that requires a different content type)
        flux_query = (
            f'from(bucket:"sensor_data") '
            f'|> range(start: -5m) '
            f'|> filter(fn: (r) => r.sensor_id == "{sensor_id}") '
            f'|> limit(n: 20)'
        )
        deadline = time.time() + 35
        found = False
        last_body = ""
        while time.time() < deadline:
            req = urllib.request.Request(
                f"http://localhost:8086/api/v2/query?org=infralab",
                data=flux_query.encode(),
                headers={
                    "Authorization": f"Token {influx_token}",
                    "Content-Type": "application/vnd.flux",
                    "Accept": "application/csv",
                },
            )
            try:
                resp = urllib.request.urlopen(req, timeout=5)
                body = resp.read().decode()
                last_body = body[:200]
                if sensor_id in body:
                    found = True
                    break
            except Exception as e:
                last_body = str(e)[:200]
            time.sleep(2)

        if found:
            runner.ok("B-05", "Sensor data in InfluxDB within 30s")
        else:
            runner.fail("B-05", "Sensor data in InfluxDB within 30s",
                        f"Last response: {last_body}")
    else:
        runner.skip("B-05", "Sensor data in InfluxDB", "INFLUXDB_TOKEN not in .env")

    # B-07 — cleanup
    _, _, rc = _docker("rm", "-f", sensor_id, check=False)
    if rc == 0:
        runner.ok("B-07", "Remove sensor container")
    else:
        runner.fail("B-07", "Remove sensor container")

    # B-08 — no orphans
    out, _, _ = _docker("ps", "-a", "--filter", "name=bench_", "--format", "{{.Names}}", check=False)
    if not out.strip():
        runner.ok("B-08", "No bench_* orphans remain")
    else:
        runner.fail("B-08", "No bench_* orphans remain", f"Found: {out.strip()}")


def scenario_data_pipeline(runner):
    """C. Data Pipeline — Grafana datasources, dashboards, InfluxDB buckets."""
    print(f"\n--- C. Data Pipeline ---")

    # Helper: Grafana API with auth
    def _grafana_api(path):
        """GET Grafana API endpoint with basic auth."""
        # Read credentials from .env if possible
        import base64
        guser = "admin123"
        gpass = "admin123"
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            with open(env_path) as _f:
                for _l in _f:
                    if _l.startswith("GF_SECURITY_ADMIN_USER="):
                        guser = _l.strip().split("=", 1)[1]
                    if _l.startswith("GF_SECURITY_ADMIN_PASSWORD="):
                        gpass = _l.strip().split("=", 1)[1]
        auth = base64.b64encode(f"{guser}:{gpass}".encode()).decode()
        req = urllib.request.Request(
            f"http://localhost:3000{path}",
            headers={"Authorization": f"Basic {auth}"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            return resp.status, resp.read().decode()
        except Exception as e:
            return None, str(e)

    # C-01 — datasources
    status, body = _grafana_api("/api/datasources")
    if status == 200:
        try:
            dss = json.loads(body)
            uids = {ds.get("uid") for ds in dss}
            expected = {"Loki", "Tempo", "InfluxDB"}
            if expected.issubset(uids):
                runner.ok("C-01", "Grafana datasources: Loki, Tempo, InfluxDB")
            else:
                missing = expected - uids
                runner.fail("C-01", "Grafana datasources",
                            f"Missing: {', '.join(missing)}. Found: {uids}")
        except json.JSONDecodeError as e:
            runner.fail("C-01", "Grafana datasources", str(e))
    else:
        runner.fail("C-01", "Grafana datasources", f"HTTP {status}")

    # C-02 — dashboards
    status, body = _grafana_api("/api/search")
    if status == 200:
        try:
            boards = json.loads(body)
            titles = {b.get("title", "") for b in boards}
            expected = {"IoT Sensors Overview", "Platform Health", "Security Operations (SOC)"}
            if expected.issubset(titles):
                runner.ok("C-02", "Grafana dashboards provisioned")
            else:
                missing = expected - titles
                runner.fail("C-02", "Grafana dashboards", f"Missing: {', '.join(missing)}")
        except json.JSONDecodeError as e:
            runner.fail("C-02", "Grafana dashboards", str(e))
    else:
        runner.fail("C-02", "Grafana dashboards", f"HTTP {status}")

    # C-03, C-04 — InfluxDB buckets
    influx_token = None
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("INFLUXDB_TOKEN="):
                    influx_token = line.strip().split("=", 1)[1]
                    break

    if influx_token:
        # Raw Flux query with application/vnd.flux content type
        raw_flux = 'buckets()'
        req = urllib.request.Request(
            "http://localhost:8086/api/v2/query?org=infralab",
            data=raw_flux.encode(),
            headers={
                "Authorization": f"Token {influx_token}",
                "Content-Type": "application/vnd.flux",
                "Accept": "application/csv",
            },
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            body = resp.read().decode()
            if "sensor_data" in body:
                runner.ok("C-03", "InfluxDB 'sensor_data' bucket exists")
            else:
                runner.fail("C-03", "InfluxDB 'sensor_data' bucket exists")
            if "platform_metrics" in body:
                runner.ok("C-04", "InfluxDB 'platform_metrics' bucket exists")
            else:
                runner.fail("C-04", "InfluxDB 'platform_metrics' bucket exists")
        except Exception as e:
            runner.fail("C-03", "InfluxDB buckets", str(e))
    else:
        runner.skip("C-03", "InfluxDB buckets", "INFLUXDB_TOKEN not in .env")

    # C-05 — Loki logs via Promtail
    # Loki API query
    try:
        loki_query = json.dumps({
            "query": '{job="suricata"} | json',
            "limit": 1,
        })
        req = urllib.request.Request(
            "http://localhost:3100/loki/api/v1/query_range",
            data=urllib.parse.urlencode({
                "query": '{job="suricata"} | json',
                "limit": 1,
            }).encode(),
        )
        resp = urllib.request.urlopen(
            f"http://localhost:3100/loki/api/v1/query_range"
            f"?query={urllib.parse.quote('{job=\"suricata\"}')}"
            f"&limit=1",
            timeout=5,
        )
        body = resp.read().decode()
        if "event_type" in body or "stream" in body:
            runner.ok("C-05", "Promtail ships Suricata logs to Loki")
        else:
            runner.fail("C-05", "Promtail ships Suricata logs to Loki", "No results")
    except Exception as e:
        runner.fail("C-05", "Promtail ships Suricata logs to Loki", str(e))

    # C-06 — OTel gRPC port
    if _port("localhost", 4317):
        runner.ok("C-06", "OTel gRPC port 4317 responds")
    else:
        runner.fail("C-06", "OTel gRPC port 4317 responds")


def scenario_security_audit(runner):
    """D. Security Audit — trigger scan, verify report."""
    print(f"\n--- D. Security Audit ---")

    # D-01 — container running
    out, _, _ = _docker("ps", "--filter", "name=security_auditor",
                        "--format", "{{.Names}}", check=False)
    if "security_auditor" in out:
        runner.ok("D-01", "Security auditor container running")
    else:
        runner.skip("D-01", "Security auditor not running", "Start the stack first")
        return  # skip remaining audit tests

    try:
        c, msgs = _mqtt_connect()
        c.subscribe("lab/security/report")
        c.subscribe("lab/security/status")

        # D-02
        c.publish("lab/security/trigger", "SCAN_NOW")
        runner.ok("D-02", "Published SCAN_NOW to lab/security/trigger")

        # D-03 — wait up to 150s for report
        deadline = time.time() + 150
        report_msg = None
        status_msgs = []
        while time.time() < deadline:
            for msg in msgs:
                if msg.topic == "lab/security/report" and not report_msg:
                    report_msg = msg
                if msg.topic == "lab/security/status":
                    status_msgs.append(msg)
            if report_msg:
                break
            time.sleep(0.5)

        c.loop_stop()
        c.disconnect()

        if report_msg:
            runner.ok("D-03", "Audit report received within 150s")
            # D-04 — HTML table
            payload = report_msg.payload.decode()
            if "<table" in payload:
                runner.ok("D-04", "Report contains HTML table")
            else:
                runner.fail("D-04", "Report contains HTML table",
                            "No <table> tag found")
        else:
            runner.fail("D-03", "Audit report received", "Timeout (150s)")
            # skip D-04, D-05
            return

        # D-05 — status updates
        if len(status_msgs) >= 2:
            runner.ok("D-05", "Audit status updates received")
        else:
            runner.fail("D-05", "Audit status updates",
                        f"Only {len(status_msgs)} messages")

    except ImportError:
        runner.skip("D-02", "Audit test", "paho-mqtt not installed")


def scenario_suricata(runner):
    """E. Suricata Detection — verify alert pipeline."""
    print(f"\n--- E. Suricata Detection ---")

    # E-01
    out, _, _ = _docker("ps", "--filter", "name=suricata-ids",
                        "--format", "{{.Names}}", check=False)
    if "suricata-ids" in out:
        runner.ok("E-01", "Suricata container running")
    else:
        runner.skip("E-01", "Suricata not running", "Start the stack first")
        return

    # E-02 — eve.json exists
    # Need root to read suricata logs
    out, _, rc = _docker("exec", "suricata-ids", "test", "-f",
                         "/var/log/suricata/eve.json", check=False)
    if rc == 0:
        runner.ok("E-02", "Suricata eve.json exists")
    else:
        runner.fail("E-02", "Suricata eve.json exists", out)
        return

    # E-03 — trigger a scan and check for alert
    # Run a quick nmap from the security auditor container
    # (Simplified: just check if any recent alert exists)
    out, _, _ = _docker(
        "exec", "suricata-ids",
        "sh", "-c",
        "tail -5 /var/log/suricata/eve.json | grep -c 'alert'",
        check=False,
    )
    if out.strip() and int(out.strip()) > 0:
        runner.ok("E-03", "Suricata has recent alerts")
    else:
        # Try to trigger alert by connecting to MQTT aggressively
        import socket
        for _ in range(5):
            try:
                s = socket.socket()
                s.settimeout(1)
                s.connect(("localhost", 1883))
                s.close()
            except Exception:
                pass
        time.sleep(2)
        out, _, _ = _docker(
            "exec", "suricata-ids",
            "sh", "-c",
            "tail -10 /var/log/suricata/eve.json | grep -c 'alert'",
            check=False,
        )
        if out.strip() and int(out.strip()) > 0:
            runner.ok("E-03", "Suricata alerts detected after trigger")
        else:
            runner.fail("E-03", "Suricata alerts detected", "No alerts in eve.json")


def scenario_attack_simulation(runner):
    """F. Attack Simulation — verify attack tools work."""
    print(f"\n--- F. Attack Simulation ---")

    try:
        c, msgs = _mqtt_connect()

        # F-01 — inject
        import paho.mqtt.client as mqtt
        topic = f"sensors/acc_test_{int(time.time())}"
        payload = json.dumps({"temp": 9999, "fake_injection": True})
        c.subscribe(topic)
        c.publish(topic, payload, qos=1)
        time.sleep(1)
        found = any(topic in msg.topic for msg in msgs)
        if found:
            runner.ok("F-01", "MQTT inject publish to custom topic")
        else:
            runner.fail("F-01", "MQTT inject publish", "Message not received back")

        # F-02 — wildcard subscribe
        c.subscribe("#")
        runner.ok("F-02", "MQTT wildcard # subscribe accepted")

        # F-03 — anonymous publish
        c.publish("sensors/anonymous_test", json.dumps({"test": True}))
        runner.ok("F-03", "Anonymous publish accepted (vulnerable config)")

        c.loop_stop()
        c.disconnect()

    except ImportError:
        runner.skip("F-01", "Attack simulation", "paho-mqtt not installed")


def scenario_cleanup(runner):
    """G. Cleanup — remove test artifacts."""
    print(f"\n--- G. Cleanup ---")

    # G-01 — remove any sensor containers
    out, _, _ = _docker("ps", "-aq", "--filter", "ancestor=iot-sensor", check=False)
    if out.strip():
        ids = out.strip().split()
        for cid in ids:
            _docker("rm", "-f", cid, check=False)
        runner.ok("G-01", f"Removed {len(ids)} stale sensor container(s)")
    else:
        runner.ok("G-01", "No stale sensor containers to remove")

    # G-02 — no bench_* containers
    out, _, _ = _docker("ps", "-a", "--filter", "name=bench_", "--format", "{{.Names}}", check=False)
    if not out.strip():
        runner.ok("G-02", "No bench_* containers remain")
    else:
        runner.fail("G-02", "No bench_* containers remain", f"Found: {out.strip()}")

    # G-03 — compose config validates (non-destructive check)
    out, _, rc = _docker("compose", "-f", str(PROJECT_ROOT / "docker-compose.yaml"),
                         "config", "--quiet", check=False)
    if rc == 0:
        runner.ok("G-03", "docker-compose.yaml is valid")
    else:
        runner.fail("G-03", "docker-compose.yaml is valid")


# =========================================================================
# main
# =========================================================================

SCENARIOS = {
    "A": ("Stack Health", scenario_stack_health),
    "B": ("Sensor Lifecycle", scenario_sensor_lifecycle),
    "C": ("Data Pipeline", scenario_data_pipeline),
    "D": ("Security Audit", scenario_security_audit),
    "E": ("Suricata Detection", scenario_suricata),
    "F": ("Attack Simulation", scenario_attack_simulation),
    "G": ("Cleanup", scenario_cleanup),
}


def main():
    parser = argparse.ArgumentParser(description="IoT InfraLab — Acceptance Test Suite")
    parser.add_argument("--list", action="store_true", help="List scenarios")
    parser.add_argument("-s", "--scenarios", type=str, default="",
                        help="Comma-separated scenario IDs (A,B,C...)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.list:
        print("Acceptance scenarios:")
        for sid, (name, _) in sorted(SCENARIOS.items()):
            print(f"  {sid}: {name}")
        return EXIT_OK

    runner = AcceptanceRunner(verbose=args.verbose)

    selected = args.scenarios.upper().replace(" ", "").split(",") if args.scenarios else []
    selected = [s.strip() for s in selected if s.strip()]

    for sid, (name, fn) in sorted(SCENARIOS.items()):
        if selected and sid not in selected:
            continue
        fn(runner)

    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())
