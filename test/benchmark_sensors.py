#!/usr/bin/env python3
"""
IoT InfraLab -- Benchmark Suite

Measurable KPIs for system startup, sensor deployment lifecycle,
scaling capacity, MQTT message latency, and resource footprint.

Usage:
    python test/benchmark_sensors.py health              # pre-flight checks
    python test/benchmark_sensors.py startup             # compose stack timing
    python test/benchmark_sensors.py deploy --count 5    # sensor lifecycle
    python test/benchmark_sensors.py scale --max 50      # scaling curve
    python test/benchmark_sensors.py latency             # MQTT throughput/latency
    python test/benchmark_sensors.py resources --sensors 10  # resource comparison
    python test/benchmark_sensors.py all                 # full suite
    python test/benchmark_sensors.py report              # export CSVs
"""

import argparse
import csv
import json
import os
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yaml"
NETWORK_NAME = "iot_infralab_net"
SENSOR_IMAGE = "iot-sensor"
SENSOR_DIR = PROJECT_ROOT / "src" / "simulation" / "docker_sensor"
REPORTS_DIR = PROJECT_ROOT / "test" / "reports"

BROKER_HOST = "localhost"
BROKER_PORT = 1883

SERVICES_WITH_PORTS = [
    ("mosquitto", "iot_broker", 1883, None),
    ("influxdb", "influxdb", 8086, "/health"),
    ("grafana", "grafana", 3000, "/api/health"),
    ("nodered", "iot_nodered", 1880, "/"),
    ("loki", "loki", 3100, "/ready"),
    ("tempo", "tempo", 4317, None),
    ("otel-collector", "otel_collector", 4318, None),
]

SERVICES_NO_PORTS = [
    ("docker-proxy", "docker_api_proxy"),
    ("telegraf", "telegraf"),
    ("promtail", "promtail"),
    ("suricata", "suricata-ids"),
    ("security-auditor", "security_auditor"),
]

ALL_SERVICES = [s[0] for s in SERVICES_WITH_PORTS + [(n, n) for n, _ in SERVICES_NO_PORTS]]

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USER_ERR = 2

# Try colorama for colored output -- graceful if missing
try:
    from colorama import init, Fore, Style

    init()
except ImportError:
    # Fallback no-op stubs
    class _DummyStyle:
        def __getattr__(self, _):
            return ""

    Fore = _DummyStyle()
    Style = _DummyStyle()


# ---------------------------------------------------------------------------
# Utility: Timer
# ---------------------------------------------------------------------------
class Timer:
    """Context manager for microsecond-precision timing."""

    __slots__ = ("_start", "_end", "elapsed")

    def __init__(self):
        self._start = 0.0
        self._end = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self._end = time.perf_counter()
        self.elapsed = (self._end - self._start) * 1000  # ms

    @property
    def elapsed_sec(self):
        return self.elapsed / 1000.0


# ---------------------------------------------------------------------------
# Utility: DockerOps -- thin subprocess wrapper
# ---------------------------------------------------------------------------
class DockerOpsError(Exception):
    pass


class DockerOps:
    """Minimal Docker CLI wrapper.  Every method returns parsed JSON."""

    @staticmethod
    def _run(*args, timeout=30, check=True):
        """Run `docker args...`, return parsed JSON."""
        cmd = ["docker"] + list(args)
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
        except FileNotFoundError:
            raise DockerOpsError("Docker CLI not found.  Is Docker installed?")
        except subprocess.TimeoutExpired:
            raise DockerOpsError(f"docker {' '.join(args)} timed out ({timeout}s)")

        if check and r.returncode != 0:
            raise DockerOpsError(
                f"docker {' '.join(args)} failed: {r.stderr.strip() or r.stdout.strip()}"
            )
        out = r.stdout.strip()
        if not out:
            return None
        # Try JSON; if it fails return raw string
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return out

    @staticmethod
    def _run_json_lines(*args, timeout=30):
        """Run docker command that emits one JSON object per line, return list."""
        cmd = ["docker"] + list(args)
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=False
            )
        except FileNotFoundError:
            raise DockerOpsError("Docker CLI not found.")
        except subprocess.TimeoutExpired:
            raise DockerOpsError("docker command timed out")

        if r.returncode != 0:
            return []
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        result = []
        for line in lines:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return result

    @staticmethod
    def create_container(image, name, env, network, auto_remove=True, binds=None):
        args = ["create", "--name", name, "--network", network]
        for k, v in env.items():
            args += ["-e", f"{k}={v}"]
        if auto_remove:
            args.append("--rm")
        if binds:
            for b in binds:
                args += ["-v", b]
        args.append(image)
        out = DockerOps._run(*args)
        return {"Id": out.strip() if isinstance(out, str) else out.get("Id", "")}

    @staticmethod
    def start_container(container_id):
        DockerOps._run("start", container_id)

    @staticmethod
    def stop_container(container_id, timeout=5):
        DockerOps._run("stop", "-t", str(timeout), container_id, check=False)

    @staticmethod
    def remove_container(container_id, force=True):
        args = ["rm"]
        if force:
            args.append("-f")
        args.append(container_id)
        DockerOps._run(*args, check=False)

    @staticmethod
    def inspect(container_id, timeout=15):
        return DockerOps._run("inspect", container_id, "--format", "{{json .}}", timeout=timeout)

    @staticmethod
    def stats(container_ids=None, timeout=15):
        """Return list of docker stats dicts for given containers (or all running if None)."""
        args = ["stats", "--no-stream", "--format", "{{json .}}"]
        if container_ids:
            args.extend(container_ids)
        return DockerOps._run_json_lines(*args, timeout=timeout)

    @staticmethod
    def list_containers(filter_name="", all_flag=True):
        args = ["ps"]
        if all_flag:
            args.append("-a")
        args.extend(["--format", "{{json .}}"])
        if filter_name:
            args.extend(["--filter", f"name={filter_name}"])
        return DockerOps._run_json_lines(*args)

    @staticmethod
    def list_images(filter_ref=""):
        args = ["images", "--format", "{{json .}}"]
        if filter_ref:
            args.extend(["--filter", f"reference={filter_ref}"])
        return DockerOps._run_json_lines(*args)

    @staticmethod
    def host_info():
        return DockerOps._run("info", "--format", "{{json .}}")

    @staticmethod
    def network_info(network_name):
        return DockerOps._run("network", "inspect", network_name, "--format", "{{json .}}")

    @staticmethod
    def compose_up(compose_file, timeout=120):
        DockerOps._run(
            "compose", "-f", str(compose_file), "up", "-d",
            timeout=timeout,
        )

    @staticmethod
    def compose_down(compose_file, volumes=False, timeout=120):
        args = ["compose", "-f", str(compose_file), "down"]
        if volumes:
            args.append("-v")
        DockerOps._run(*args, timeout=timeout)

    @staticmethod
    def build_sensor_image(sensor_dir, timeout=120):
        DockerOps._run(
            "build", "-t", SENSOR_IMAGE, str(sensor_dir),
            timeout=timeout,
        )

    @staticmethod
    def container_logs(container_id, tail=50):
        return DockerOps._run("logs", "--tail", str(tail), container_id, check=False)


# ---------------------------------------------------------------------------
# Utility: MQTT Monitor
# ---------------------------------------------------------------------------
class MQTTMonitor:
    """Subscribe to sensor topics, track first-message events, compute latency."""

    def __init__(self, host=BROKER_HOST, port=BROKER_PORT, client_id=None):
        self.host = host
        self.port = port
        self._client = None
        self._messages = defaultdict(list)  # sensor_id -> [dict]
        self._first_events = {}  # sensor_id -> threading.Event
        self._first_payloads = {}  # sensor_id -> dict
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._stop_collect = threading.Event()
        self._collect_done = threading.Event()
        self._mqtt_ok = False

        import paho.mqtt.client as mqtt

        cid = client_id or f"bench_monitor_{os.getpid()}_{int(time.time())}"
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, cid)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reasonCode, properties=None):
        if reasonCode == 0:
            self._connected.set()
            self._mqtt_ok = True

    def _on_message(self, client, userdata, msg):
        topic = msg.topic  # sensors/factory/{sensor_id}
        parts = topic.split("/")
        if len(parts) < 3:
            return
        sensor_id = parts[-1]
        arrival = time.time()
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        record = {"arrival": arrival, "payload": payload}

        with self._lock:
            self._messages[sensor_id].append(record)
            # Always ensure event exists and is set -- handles race where
            # wait_for_first_message created the Event entry before we ran
            if sensor_id not in self._first_events:
                self._first_events[sensor_id] = threading.Event()
            self._first_events[sensor_id].set()
            self._first_payloads[sensor_id] = payload

    def start(self, timeout=10):
        self._client.connect(self.host, self.port, 60)
        self._client.loop_start()
        if not self._connected.wait(timeout):
            raise TimeoutError(f"MQTT connection to {self.host}:{self.port} timed out")

    def stop(self):
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass

    def subscribe_all_sensors(self):
        self._client.subscribe("sensors/factory/+")
        time.sleep(0.5)  # let SUBSCRIBE reach broker

    def subscribe(self, topic):
        self._client.subscribe(topic)

    def wait_for_first_message(self, sensor_id, timeout=60):
        if sensor_id not in self._first_events:
            self._first_events[sensor_id] = threading.Event()
        ev = self._first_events[sensor_id]
        ok = ev.wait(timeout)
        if ok:
            return self._first_payloads.get(sensor_id)
        return None

    def wait_for_all_expected(self, sensor_ids, timeout=60):
        results = {}
        deadline = time.time() + timeout
        for sid in sensor_ids:
            remaining = max(0, deadline - time.time())
            payload = self.wait_for_first_message(sid, remaining)
            results[sid] = payload
        return results

    def collect_for_duration(self, duration):
        self._stop_collect.clear()
        self._collect_done.clear()
        # Let the loop run for 'duration' seconds in a bg thread
        def _wait():
            self._stop_collect.wait(duration)
            self._collect_done.set()

        t = threading.Thread(target=_wait, daemon=True)
        t.start()
        self._collect_done.wait(duration + 5)

    def get_messages(self, sensor_id=None):
        with self._lock:
            if sensor_id:
                return list(self._messages.get(sensor_id, []))
            return dict(self._messages)

    def latency_stats(self, sensor_id=None):
        """Compute latency percentiles from receive_time - payload.timestamp (ms)."""
        all_latencies = []
        with self._lock:
            sources = (
                [sensor_id]
                if sensor_id
                else list(self._messages.keys())
            )
            for sid in sources:
                for rec in self._messages.get(sid, []):
                    ts = rec["payload"].get("timestamp")
                    if ts is None:
                        continue
                    lat_ms = (rec["arrival"] - ts) * 1000
                    all_latencies.append(lat_ms)

        if not all_latencies:
            return {
                "p50_ms": None, "p75_ms": None, "p90_ms": None,
                "p95_ms": None, "p99_ms": None, "max_ms": None,
                "min_ms": None, "mean_ms": None, "stddev_ms": None,
                "count": 0,
            }

        all_latencies.sort()
        n = len(all_latencies)
        return {
            "p50_ms": round(all_latencies[int(n * 0.50)], 2),
            "p75_ms": round(all_latencies[int(n * 0.75)], 2),
            "p90_ms": round(all_latencies[int(n * 0.90)], 2),
            "p95_ms": round(all_latencies[int(n * 0.95)], 2),
            "p99_ms": round(all_latencies[int(n * 0.99)], 2),
            "max_ms": round(all_latencies[-1], 2),
            "min_ms": round(all_latencies[0], 2),
            "mean_ms": round(statistics.mean(all_latencies), 2) if n else None,
            "stddev_ms": round(statistics.stdev(all_latencies), 2) if n > 1 else 0.0,
            "count": n,
        }

    @property
    def message_counts(self):
        with self._lock:
            return {sid: len(msgs) for sid, msgs in self._messages.items()}


# ---------------------------------------------------------------------------
# Utility: Port / HTTP ready checks
# ---------------------------------------------------------------------------
def port_ready(host, port, timeout=30, interval=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except (OSError, socket.timeout):
            time.sleep(interval)
    raise TimeoutError(f"Port {host}:{port} not ready after {timeout}s")


def http_ready(host, port, path="/", timeout=30, interval=0.5):
    import urllib.request
    import urllib.error

    url = f"http://{host}:{port}{path}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status < 500:
                return
        except (urllib.error.URLError, OSError, socket.timeout):
            time.sleep(interval)
    raise TimeoutError(f"HTTP {url} not ready after {timeout}s")


def wait_for_container_running(container_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            info = DockerOps.inspect(container_id)
            if info and isinstance(info, dict):
                state = info.get("State", {})
            elif info and isinstance(info, list):
                state = info[0].get("State", {})
            else:
                state = {}
            if state.get("Running"):
                return
        except DockerOpsError:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Container {container_id} not running after {timeout}s")


# ---------------------------------------------------------------------------
# Utility: parse docker stats values
# ---------------------------------------------------------------------------
def parse_memory_mb(mem_usage_str):
    """Parse '15.2MiB / 256MiB' or '120.5MB / 1.2GB' -> MB (float)."""
    if not mem_usage_str:
        return 0.0
    used = mem_usage_str.split("/")[0].strip()
    # Handle MiB / GiB / KiB
    if "MiB" in used:
        return float(used.replace("MiB", "").strip())
    elif "GiB" in used:
        return float(used.replace("GiB", "").strip()) * 1024
    elif "KiB" in used:
        return float(used.replace("KiB", "").strip()) / 1024
    elif "MB" in used:
        return float(used.replace("MB", "").strip())
    elif "GB" in used:
        return float(used.replace("GB", "").strip()) * 1000
    elif "kB" in used:
        return float(used.replace("kB", "").strip()) / 1000
    elif "B" in used and not any(c in used for c in "iGMK"):
        return float(used.replace("B", "").strip()) / (1024 * 1024)
    try:
        return float(used)
    except ValueError:
        return 0.0


def parse_cpu_percent(cpu_str):
    """Parse '0.25%' or '2.50%' -> float."""
    if not cpu_str:
        return 0.0
    return float(cpu_str.replace("%", "").strip())


# ---------------------------------------------------------------------------
# Utility: validate sensor payload
# ---------------------------------------------------------------------------
def validate_sensor_payload(payload):
    if not payload or not isinstance(payload, dict):
        return False
    required = {"sensor_id", "readings", "timestamp"}
    if not required.issubset(payload.keys()):
        return False
    if not isinstance(payload["readings"], dict):
        return False
    return True


# ---------------------------------------------------------------------------
# Utility: sensor name pattern & cleanup
# ---------------------------------------------------------------------------
def bench_name(cmd, n):
    return f"bench_{cmd}_{n}"


def is_bench_container(name):
    return name and name.startswith("bench_")


def cleanup_bench_sensors():
    """Force-remove all containers with names starting with `bench_`."""
    containers = DockerOps.list_containers(filter_name="bench_")
    for c in containers:
        cid = c.get("ID", "")
        if cid:
            DockerOps.remove_container(cid, force=True)
    # Verify
    remaining = DockerOps.list_containers(filter_name="bench_")
    return len(remaining)


def deploy_one_sensor(sid, profile="normal", interval=5, sensor_types="temperature", timeout=60):
    """Deploy a single sensor container, return dict with timing and result."""
    result = {"sensor_id": sid, "ok": False, "error": None}

    # CREATE
    with Timer() as t:
        try:
            create_resp = DockerOps.create_container(
                image=SENSOR_IMAGE,
                name=sid,
                env={
                    "SENSOR_ID": sid,
                    "SENSOR_TYPES": sensor_types,
                    "NODE_PROFILE": profile,
                    "INTERVAL": str(interval),
                    "MQTT_BROKER": "mosquitto",
                },
                network=NETWORK_NAME,
            )
        except DockerOpsError as e:
            result["error"] = f"create failed: {e}"
            return result
    result["api_create_ms"] = round(t.elapsed, 1)

    container_id = create_resp.get("Id", "")

    # START
    with Timer() as t:
        try:
            DockerOps.start_container(container_id)
        except DockerOpsError as e:
            result["error"] = f"start failed: {e}"
            return result
    result["api_start_ms"] = round(t.elapsed, 1)
    result["container_id"] = container_id

    # WAIT for container running
    with Timer() as t:
        try:
            wait_for_container_running(container_id, timeout=15)
        except TimeoutError as e:
            result["error"] = f"container not running: {e}"
            result["container_running_lag_ms"] = round(t.elapsed, 1)
            return result
    result["container_running_lag_ms"] = round(t.elapsed, 1)

    result["ok"] = True
    return result


# ---------------------------------------------------------------------------
# Utility: Reporter
# ---------------------------------------------------------------------------
class Reporter:
    """Accumulates results and writes JSON/CSV output."""

    def __init__(self, args=None):
        self.start_time = datetime.now(timezone.utc)
        self.results = {}
        self.warnings = []
        self.errors = []
        self.args = args

    def set_result(self, category, data):
        self.results[category] = data

    def add_warning(self, msg):
        self.warnings.append(msg)

    def add_error(self, msg):
        self.errors.append(msg)

    def _host_info(self):
        try:
            info = DockerOps.host_info()
            if isinstance(info, dict):
                return {
                    "docker_version": info.get("ServerVersion", "unknown"),
                    "os": info.get("OperatingSystem", "unknown"),
                    "cpu_count": info.get("NCPU", 0),
                    "total_memory_gb": round(
                        info.get("MemTotal", 0) / (1024 ** 3), 1
                    ),
                    "server_arch": info.get("Architecture", "unknown"),
                    "storage_driver": (
                        info.get("Driver", "")
                        if isinstance(info.get("Driver"), str)
                        else (info.get("Driver", {})).get("Name", "")
                    ),
                }
        except Exception:
            pass
        return {}

    def to_dict(self):
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return {
            "meta": {
                "suite": self.args.command if self.args else "unknown",
                "version": "1.0.0",
                "timestamp": self.start_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "host_info": self._host_info(),
                "args": {k: v for k, v in vars(self.args).items() if v is not None}
                if self.args else {},
            },
            "results": self.results,
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def to_json(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def to_csv(self, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        files = []

        # startup -> startup_timing.csv
        if "startup" in self.results:
            rows = []
            svcs = self.results["startup"].get("per_service_ready_time", {})
            for name, info in svcs.items():
                rows.append({
                    "service": name,
                    "ready_seconds": info.get("ready_seconds", ""),
                    "port": info.get("port", ""),
                    "notes": info.get("note", ""),
                })
            if rows:
                path = output_dir / "startup_timing.csv"
                _write_csv(path, rows)
                files.append(str(path))

        # deploy -> deploy_timing.csv
        if "deploy" in self.results:
            rows = self.results["deploy"].get("sensors", [])
            if rows:
                path = output_dir / "deploy_timing.csv"
                _write_csv(path, rows)
                files.append(str(path))

        # scaling -> scaling.csv
        if "scaling" in self.results:
            rows = []
            levels = self.results["scaling"].get("load_levels", {})
            for level, data in sorted(levels.items(), key=lambda x: int(x[0])):
                rows.append({
                    "sensor_count": level,
                    "total_memory_mb": data.get("total_memory_mb", ""),
                    "mean_cpu_percent": data.get("mean_cpu_percent", ""),
                    "memory_per_sensor_mb": data.get("memory_per_sensor_mb", ""),
                })
            if rows:
                path = output_dir / "scaling.csv"
                _write_csv(path, rows)
                files.append(str(path))

        # mqtt_latency -> mqtt_latency.csv
        if "mqtt_latency" in self.results:
            rows = []
            levels = self.results["mqtt_latency"].get("by_load_level", {})
            for count, data in sorted(levels.items(), key=lambda x: int(x[0])):
                rows.append({
                    "sensor_count": count,
                    "p50_ms": data.get("p50_ms", ""),
                    "p95_ms": data.get("p95_ms", ""),
                    "p99_ms": data.get("p99_ms", ""),
                    "mean_ms": data.get("mean_ms", ""),
                    "max_ms": data.get("max_ms", ""),
                    "delivery_rate": data.get("delivery_rate", ""),
                    "messages_received": data.get("total_messages_received", ""),
                })
            if rows:
                path = output_dir / "mqtt_latency.csv"
                _write_csv(path, rows)
                files.append(str(path))

        # resources -> resources.csv
        if "resources" in self.results:
            rows = []
            for state in ("idle", "loaded"):
                data = self.results["resources"].get(state, {})
                rows.append({
                    "state": state,
                    "sensor_count": data.get("sensor_count", 0),
                    "platform_memory_mb": data.get("platform_memory_mb", ""),
                    "platform_cpu_percent": data.get("platform_cpu_percent", ""),
                    "per_sensor_memory_mb": data.get("per_sensor_memory_mb", ""),
                    "per_sensor_cpu_percent": data.get("per_sensor_cpu_percent", ""),
                })
            if rows:
                path = output_dir / "resources.csv"
                _write_csv(path, rows)
                files.append(str(path))

        return files

    def print_summary(self):
        print(f"\n{'=' * 60}")
        print(f" Benchmark Summary")
        print(f"{'=' * 60}")
        for cat, data in self.results.items():
            print(f"  {cat}:")
            if isinstance(data, dict):
                for k, v in list(data.items())[:8]:  # top 8 keys
                    if isinstance(v, (int, float, str, bool)):
                        print(f"    {k}: {v}")
            print()

        if self.warnings:
            print(f"  {Fore.YELLOW}Warnings ({len(self.warnings)}):{Style.RESET_ALL}")
            for w in self.warnings:
                print(f"    {w}")
        if self.errors:
            print(f"  {Fore.RED}Errors ({len(self.errors)}):{Style.RESET_ALL}")
            for e in self.errors:
                print(f"    {e}")
        print(f"{'=' * 60}")


def _write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ===================================================================
# COMMAND: health
# ===================================================================
def cmd_health(args, reporter):
    """Pre-flight checks before benchmarks."""
    print(f"\n{'=' * 60}")
    print(f" Pre-flight Health Check")
    print(f"{'=' * 60}")

    checks = []
    passed = 0
    failed = 0

    # 1. Docker reachable
    print(f"\n[1/7] Docker daemon ...................... ", end="", flush=True)
    try:
        info = DockerOps.host_info()
        ver = info.get("ServerVersion", "?") if isinstance(info, dict) else "?"
        print(f"{Fore.GREEN}OK{Style.RESET_ALL} (v{ver})")
        passed += 1
    except DockerOpsError as e:
        print(f"{Fore.RED}FAIL{Style.RESET_ALL} -- {e}")
        failed += 1
        reporter.add_error(f"Docker daemon unreachable: {e}")

    # 2. iot-sensor image
    print(f"[2/7] Sensor image ({SENSOR_IMAGE}) ......... ", end="", flush=True)
    try:
        images = DockerOps.list_images(filter_ref=SENSOR_IMAGE)
        if images:
            size = images[0].get("Size", "?")
            print(f"{Fore.GREEN}OK{Style.RESET_ALL} ({size})")
            passed += 1
        else:
            print(f"{Fore.YELLOW}MISSING{Style.RESET_ALL} -- build with: docker compose build")
            reporter.add_warning(f"Image {SENSOR_IMAGE} not found. Run: docker compose build")
            passed += 1  # soft fail
    except DockerOpsError as e:
        print(f"{Fore.RED}FAIL{Style.RESET_ALL} -- {e}")
        failed += 1

    # 3. Network
    print(f"[3/7] Network ({NETWORK_NAME}) ............. ", end="", flush=True)
    try:
        DockerOps.network_info(NETWORK_NAME)
        print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        passed += 1
    except DockerOpsError:
        print(f"{Fore.YELLOW}MISSING{Style.RESET_ALL} -- start stack first")
        reporter.add_warning(f"Network {NETWORK_NAME} not found")
        passed += 1

    # 4. MQTT Broker
    print(f"[4/7] MQTT Broker ({BROKER_HOST}:{BROKER_PORT}) .. ", end="", flush=True)
    try:
        port_ready(BROKER_HOST, BROKER_PORT, timeout=3)
        print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        passed += 1
    except TimeoutError:
        print(f"{Fore.YELLOW}DOWN{Style.RESET_ALL} -- stack may not be running")
        reporter.add_warning("MQTT broker not reachable")
        passed += 1

    # 5. InfluxDB
    print(f"[5/7] InfluxDB (:8086) ................... ", end="", flush=True)
    try:
        http_ready(BROKER_HOST, 8086, "/health", timeout=3)
        print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        passed += 1
    except TimeoutError:
        print(f"{Fore.YELLOW}DOWN{Style.RESET_ALL}")
        reporter.add_warning("InfluxDB not reachable")
        passed += 1

    # 6. Grafana
    print(f"[6/7] Grafana (:3000) .................... ", end="", flush=True)
    try:
        http_ready(BROKER_HOST, 3000, "/api/health", timeout=3)
        print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        passed += 1
    except TimeoutError:
        print(f"{Fore.YELLOW}DOWN{Style.RESET_ALL}")
        reporter.add_warning("Grafana not reachable")
        passed += 1

    # 7. Node-RED
    print(f"[7/7] Node-RED (:1880) ................... ", end="", flush=True)
    try:
        http_ready(BROKER_HOST, 1880, "/", timeout=3)
        print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        passed += 1
    except TimeoutError:
        print(f"{Fore.YELLOW}DOWN{Style.RESET_ALL}")
        reporter.add_warning("Node-RED not reachable")
        passed += 1

    # Check orphaned bench containers
    orphans = DockerOps.list_containers(filter_name="bench_")
    if orphans:
        reporter.add_warning(
            f"Found {len(orphans)} orphaned bench_* containers. "
            f"Run cleanup or 'python test/benchmark_sensors.py deploy --clean'"
        )

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f" Health: {passed}/{total} passed")
    if failed:
        print(f" {Fore.RED}{failed} FAILURES -- fix before running benchmarks{Style.RESET_ALL}")
    else:
        print(f" {Fore.GREEN}All checks passed -- ready to benchmark{Style.RESET_ALL}")
    print(f"{'=' * 60}")

    reporter.set_result("health", {
        "passed": passed,
        "failed": failed,
        "total": total,
    })

    return EXIT_OK if failed == 0 else EXIT_FAIL


# ===================================================================
# COMMAND: startup
# ===================================================================
def cmd_startup(args, reporter):
    """Measure docker compose startup time + per-service readiness."""
    print(f"\n{'=' * 60}")
    print(f" Startup Timing Benchmark")
    print(f"{'=' * 60}")

    if not args.skip_down:
        print(f"\n{Fore.YELLOW}Taking stack down...{Style.RESET_ALL}")
        DockerOps.compose_down(args.compose_file, volumes=False)
        time.sleep(2)
        print(f"Stack down.")

    print(f"{Fore.YELLOW}Starting stack...{Style.RESET_ALL}")
    t0 = time.perf_counter()
    DockerOps.compose_up(args.compose_file)
    wall_time = time.perf_counter() - t0
    print(f" docker compose up -d: {Fore.CYAN}{wall_time:.1f}s{Style.RESET_ALL}\n")

    ready_times = {}

    # Services with exposed ports
    for name, container_name, port, http_path in SERVICES_WITH_PORTS:
        print(f"  Waiting for {name} ({container_name}) ... ", end="", flush=True)
        t1 = time.perf_counter()
        try:
            if http_path:
                http_ready(BROKER_HOST, port, http_path, timeout=args.timeout)
            else:
                port_ready(BROKER_HOST, port, timeout=args.timeout)
            elapsed = time.perf_counter() - t1
            print(f"{Fore.GREEN}OK{Style.RESET_ALL} ({elapsed:.1f}s)")
            entry = {"ready_seconds": round(elapsed, 1), "port": port}
            ready_times[name] = entry
        except TimeoutError:
            elapsed = time.perf_counter() - t1
            print(f"{Fore.RED}TIMEOUT{Style.RESET_ALL} ({elapsed:.1f}s)")
            reporter.add_warning(f"{name}: not ready within {args.timeout}s")
            entry = {"ready_seconds": round(elapsed, 1), "port": port, "timed_out": True}
            ready_times[name] = entry

    # Services without exposed ports (check via docker inspect)
    for name, container_name in SERVICES_NO_PORTS:
        print(f"  Waiting for {name} ({container_name}) ... ", end="", flush=True)
        t1 = time.perf_counter()
        try:
            # Get container ID
            containers = DockerOps.list_containers(filter_name=container_name)
            if containers:
                cid = containers[0].get("ID", "")
                wait_for_container_running(cid, timeout=args.timeout)
                elapsed = time.perf_counter() - t1
                print(f"{Fore.GREEN}OK{Style.RESET_ALL} ({elapsed:.1f}s)")
                ready_times[name] = {
                    "ready_seconds": round(elapsed, 1),
                    "port": None,
                    "note": "no exposed port",
                }
            else:
                elapsed = time.perf_counter() - t1
                print(f"{Fore.YELLOW}NOT FOUND{Style.RESET_ALL} ({elapsed:.1f}s)")
                reporter.add_warning(f"{name}: container '{container_name}' not found")
                ready_times[name] = {
                    "ready_seconds": round(elapsed, 1),
                    "port": None,
                    "note": "container not found",
                }
        except TimeoutError:
            elapsed = time.perf_counter() - t1
            print(f"{Fore.RED}TIMEOUT{Style.RESET_ALL} ({elapsed:.1f}s)")
            ready_times[name] = {
                "ready_seconds": round(elapsed, 1),
                "port": None,
                "note": "timed out",
            }

    if ready_times:
        stack_ready = max(
            v["ready_seconds"] for v in ready_times.values()
        )
    else:
        stack_ready = 0

    # Sort by ready time
    startup_order = sorted(ready_times, key=lambda s: ready_times[s]["ready_seconds"])

    print(f"\n  {Fore.CYAN}Stack ready: {stack_ready:.1f}s  "
          f"(docker compose up: {wall_time:.1f}s){Style.RESET_ALL}")
    print(f"  Startup order: {', '.join(startup_order[:5])}...")

    reporter.set_result("startup", {
        "docker_compose_up_wall_time": round(wall_time, 1),
        "stack_ready_time": stack_ready,
        "per_service_ready_time": ready_times,
        "startup_order": startup_order,
    })

    return EXIT_OK


# ===================================================================
# COMMAND: deploy
# ===================================================================
def cmd_deploy(args, reporter):
    """Measure individual sensor deployment lifecycle timing."""
    print(f"\n{'=' * 60}")
    print(f" Sensor Deployment Lifecycle Benchmark")
    print(f"{'=' * 60}")

    # Clean first
    cleanup_bench_sensors()
    time.sleep(1)

    # Check image
    images = DockerOps.list_images(filter_ref=SENSOR_IMAGE)
    if not images:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} Image '{SENSOR_IMAGE}' not found. "
              f"Build with: docker build -t {SENSOR_IMAGE} {SENSOR_DIR}")
        reporter.add_error(f"Sensor image '{SENSOR_IMAGE}' not found")
        return EXIT_FAIL

    # Start MQTT monitor
    try:
        monitor = MQTTMonitor()
        monitor.start()
        monitor.subscribe_all_sensors()
    except (ImportError, TimeoutError) as e:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} MQTT setup failed: {e}")
        reporter.add_error(f"MQTT setup failed: {e}")
        return EXIT_FAIL

    sensor_ids = [bench_name("deploy", i + 1) for i in range(args.count)]
    measurements = []

    print(f"\nDeploying {args.count} sensor(s) (profile={args.profile}, "
          f"interval={args.interval}s, types={args.types}):\n")

    for sid in sensor_ids:
        sensor = {"sensor_id": sid}

        # Deploy
        with Timer() as t_total:
            result = deploy_one_sensor(
                sid, profile=args.profile, interval=args.interval,
                sensor_types=args.types,
            )

        if not result.get("ok"):
            sensor["error"] = result.get("error", "unknown")
            # Fill missing fields for CSV consistency
            for k in ("api_create_ms", "api_start_ms", "container_running_lag_ms",
                      "first_mqtt_ms", "total_lifecycle_ms", "payload_valid"):
                sensor.setdefault(k, None)
            measurements.append(sensor)
            print(f"  [{sid}] {Fore.RED}FAIL{Style.RESET_ALL} -- {sensor['error']}")
            reporter.add_error(f"Deploy failed: {sid} -- {sensor['error']}")
            continue

        container_id = result.get("container_id", "")
        sensor["api_create_ms"] = result["api_create_ms"]
        sensor["api_start_ms"] = result["api_start_ms"]
        sensor["container_running_lag_ms"] = result["container_running_lag_ms"]

        # Wait for first MQTT message
        with Timer() as t_mqtt:
            payload = monitor.wait_for_first_message(sid, timeout=60)

        sensor["first_mqtt_ms"] = round(t_mqtt.elapsed, 1) if payload else None
        sensor["payload_valid"] = validate_sensor_payload(payload) if payload else False

        # Total lifecycle
        lifecycle = (
            (sensor["api_create_ms"] or 0)
            + (sensor["api_start_ms"] or 0)
            + (sensor["container_running_lag_ms"] or 0)
            + (sensor["first_mqtt_ms"] or 0)
        )
        sensor["total_lifecycle_ms"] = round(lifecycle, 1)

        measurements.append(sensor)

        status = (
            f"{Fore.GREEN}OK{Style.RESET_ALL}"
            if sensor["payload_valid"]
            else f"{Fore.RED}INVALID{Style.RESET_ALL}"
        )
        print(f"  [{sid}] create={sensor['api_create_ms']}ms "
              f"start={sensor['api_start_ms']}ms "
              f"run={sensor.get('container_running_lag_ms', '?')}ms "
              f"mqtt={sensor.get('first_mqtt_ms', '?')}ms "
              f"lifecycle={sensor.get('total_lifecycle_ms', '?')}ms {status}")

    monitor.stop()

    # Aggregate
    valid_ms = [
        m["total_lifecycle_ms"]
        for m in measurements
        if m.get("total_lifecycle_ms") is not None
    ]
    first_mqtts = [
        m["first_mqtt_ms"]
        for m in measurements
        if m.get("first_mqtt_ms") is not None
    ]

    aggregate = {}
    if valid_ms:
        aggregate.update({
            "mean_lifecycle_ms": round(statistics.mean(valid_ms), 1),
            "median_lifecycle_ms": round(statistics.median(valid_ms), 1),
            "min_lifecycle_ms": round(min(valid_ms), 1),
            "max_lifecycle_ms": round(max(valid_ms), 1),
            "stddev_lifecycle_ms": round(statistics.stdev(valid_ms), 1)
            if len(valid_ms) > 1 else 0,
        })
    if first_mqtts:
        aggregate["mean_first_mqtt_ms"] = round(statistics.mean(first_mqtts), 1)
        sorted_ms = sorted(first_mqtts)
        aggregate["p95_first_mqtt_ms"] = round(
            sorted_ms[int(len(sorted_ms) * 0.95)], 1
        )

    reporter.set_result("deploy", {
        "count": args.count,
        "sensor_image": SENSOR_IMAGE,
        "profile": args.profile,
        "interval_sec": args.interval,
        "sensor_types": args.types,
        "sensors": measurements,
        "aggregate": aggregate,
    })

    # Cleanup
    print(f"\n{Fore.YELLOW}Cleaning up sensors...{Style.RESET_ALL}")
    remaining = cleanup_bench_sensors()
    print(f"Cleanup complete ({remaining} remaining)")

    return EXIT_OK


# ===================================================================
# COMMAND: scale
# ===================================================================
def cmd_scale(args, reporter):
    """Measure scaling curve: deploy N sensors, measure resource usage."""
    print(f"\n{'=' * 60}")
    print(f" Sensor Scaling Benchmark")
    print(f"{'=' * 60}")

    # Build load levels: step from 1 to max
    levels = list(range(1, args.max + 1, args.step))
    if levels[-1] != args.max:
        levels.append(args.max)

    # Check image
    images = DockerOps.list_images(filter_ref=SENSOR_IMAGE)
    if not images:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} Image '{SENSOR_IMAGE}' not found.")
        reporter.add_error(f"Sensor image '{SENSOR_IMAGE}' not found")
        return EXIT_FAIL

    # MQTT monitor
    try:
        monitor = MQTTMonitor()
        monitor.start()
        monitor.subscribe_all_sensors()
    except (ImportError, TimeoutError) as e:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} MQTT setup failed: {e}")
        reporter.add_error(f"MQTT setup failed: {e}")
        return EXIT_FAIL

    scaling_data = {}
    failure_point = None
    total_deployed = 0

    print(f"\nScaling: 1 -> {args.max} sensors (step={args.step}, parallel={args.parallel})\n")

    for target in levels:
        to_create = target - total_deployed
        if to_create <= 0:
            continue

        batch_ids = [
            bench_name("scale", total_deployed + i + 1)
            for i in range(to_create)
        ]

        print(f"  Load {target}: deploying {len(batch_ids)} sensor(s)... ", end="", flush=True)

        # Parallel deploy
        errors = []
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            futures = {
                pool.submit(
                    deploy_one_sensor, sid, args.profile, args.interval, args.types
                ): sid
                for sid in batch_ids
            }
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    result = future.result()
                    if not result.get("ok"):
                        errors.append(f"{sid}: {result.get('error', 'unknown')}")
                except Exception as e:
                    errors.append(f"{sid}: {e}")

        if errors:
            failure_point = target
            print(f"{Fore.RED}FAIL{Style.RESET_ALL} ({len(errors)} errors)")
            for e in errors[:3]:
                print(f"           {e}")
                reporter.add_error(f"Scale failure at {target}: {e}")
            break

        # Wait for first MQTT from all sensors in this batch
        monitor.wait_for_all_expected(batch_ids, timeout=60)
        total_deployed += len(batch_ids)

        # Stabilize
        time.sleep(2)

        # Collect docker stats for all bench containers
        all_bench = DockerOps.list_containers(filter_name="bench_scale_")
        stats_data = DockerOps.stats([c["ID"] for c in all_bench]) if all_bench else []

        total_mem = sum(
            parse_memory_mb(s.get("MemUsage", "")) for s in stats_data
        )
        total_cpu = sum(
            parse_cpu_percent(s.get("CPUPerc", "")) for s in stats_data
        )
        count = len(all_bench)

        entry = {
            "count": count,
            "total_memory_mb": round(total_mem, 1),
            "mean_cpu_percent": round(total_cpu / max(count, 1), 2),
            "memory_per_sensor_mb": round(total_mem / max(count, 1), 1),
            "cpu_per_sensor_percent": round(total_cpu / max(count, 1), 4),
        }
        scaling_data[str(target)] = entry

        print(f"{Fore.GREEN}{count} sensors{Style.RESET_ALL}, "
              f"{entry['total_memory_mb']}MB total, "
              f"{entry['memory_per_sensor_mb']}MB/sensor, "
              f"{entry['cpu_per_sensor_percent']}% CPU/sensor")

    monitor.stop()

    # Cleanup
    print(f"\n{Fore.YELLOW}Cleaning up all sensors...{Style.RESET_ALL}")
    t0 = time.perf_counter()
    remaining = cleanup_bench_sensors()
    cleanup_time = time.perf_counter() - t0
    print(f"Cleanup: {cleanup_time:.1f}s ({remaining} remaining)")

    reporter.set_result("scaling", {
        "max_sensors_attempted": args.max,
        "max_sensors_succeeded": total_deployed,
        "failure_point": failure_point,
        "failure_reason": None,
        "cleanup_time_seconds": round(cleanup_time, 1),
        "load_levels": scaling_data,
    })

    # Simple extrapolation
    mem_per_sensor_values = [
        v["memory_per_sensor_mb"]
        for v in scaling_data.values()
        if v.get("memory_per_sensor_mb")
    ]
    if mem_per_sensor_values:
        avg_mem = statistics.mean(mem_per_sensor_values)
        reporter.set_result("scaling_extrapolation", {
            "memory_mb_formula": f"{avg_mem:.1f} * N",
            "avg_memory_per_sensor_mb": round(avg_mem, 1),
        })

    return EXIT_OK


# ===================================================================
# COMMAND: latency
# ===================================================================
def cmd_latency(args, reporter):
    """Measure MQTT message latency at various sensor load levels."""
    print(f"\n{'=' * 60}")
    print(f" MQTT Latency / Throughput Benchmark")
    print(f"{'=' * 60}")

    sensor_counts = [int(x.strip()) for x in args.sensor_counts.split(",")]

    # Check image
    images = DockerOps.list_images(filter_ref=SENSOR_IMAGE)
    if not images:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} Image '{SENSOR_IMAGE}' not found.")
        reporter.add_error(f"Sensor image '{SENSOR_IMAGE}' not found")
        return EXIT_FAIL

    by_load = {}
    total_passed = 0
    total_failed = 0

    for count in sensor_counts:
        print(f"\n{'-' * 40}")
        print(f" Load level: {count} sensor(s)")
        print(f"{'-' * 40}")

        cleanup_bench_sensors()
        time.sleep(1)

        # MQTT monitor
        try:
            monitor = MQTTMonitor()
            monitor.start()
            monitor.subscribe_all_sensors()
        except (ImportError, TimeoutError) as e:
            print(f"  {Fore.RED}MQTT setup failed: {e}{Style.RESET_ALL}")
            reporter.add_error(f"MQTT setup failed at count {count}: {e}")
            total_failed += 1
            continue

        # Deploy
        ids = []
        with ThreadPoolExecutor(max_workers=min(3, count)) as pool:
            futures = {
                pool.submit(
                    deploy_one_sensor,
                    bench_name("lat", i + 1),
                    args.profile, args.interval, args.types,
                ): i
                for i in range(count)
            }
            for future in as_completed(futures):
                result = future.result()
                if result.get("ok"):
                    ids.append(result["sensor_id"])

        if len(ids) < count:
            print(f"  {Fore.RED}Deployed only {len(ids)}/{count} sensors{Style.RESET_ALL}")
            reporter.add_warning(f"Latency test: deployed {len(ids)}/{count} at load {count}")

        # Wait for first messages
        monitor.wait_for_all_expected(ids, timeout=60)
        time.sleep(2)  # stabilization

        # Collect messages
        print(f"  Collecting messages for {args.duration}s ... ", end="", flush=True)
        t_collect_start = time.time()
        monitor.collect_for_duration(args.duration)
        actual_duration = time.time() - t_collect_start

        # Stats
        all_counts = monitor.message_counts
        total_msgs = sum(all_counts.values())
        expected = count * (args.duration / args.interval)
        delivery = round(total_msgs / max(expected, 1), 4)

        stats = monitor.latency_stats()
        stats["sensor_count"] = count
        stats["duration_seconds"] = round(actual_duration, 1)
        stats["total_messages_received"] = total_msgs
        stats["expected_messages"] = round(expected, 1)
        stats["delivery_rate"] = delivery

        by_load[str(count)] = stats

        if delivery >= 0.95:
            total_passed += 1
            print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        else:
            total_failed += 1
            print(f"{Fore.YELLOW}LOW DELIVERY{Style.RESET_ALL} ({delivery})")

        print(f"    Messages: {total_msgs}/{expected:.0f} "
              f"(delivery={delivery})")
        print(f"    Latency: p50={stats['p50_ms']}ms "
              f"p95={stats['p95_ms']}ms "
              f"p99={stats['p99_ms']}ms")
        print(f"    Throughput: {total_msgs / max(actual_duration, 1):.1f} msgs/s")

        monitor.stop()
        cleanup_bench_sensors()

    reporter.set_result("mqtt_latency", {
        "interval_sec": args.interval,
        "by_load_level": by_load,
    })

    return EXIT_OK


# ===================================================================
# COMMAND: resources
# ===================================================================
def cmd_resources(args, reporter):
    """Compare resource footprint idle vs loaded."""
    print(f"\n{'=' * 60}")
    print(f" Resource Footprint Benchmark")
    print(f"{'=' * 60}")

    # Check image
    images = DockerOps.list_images(filter_ref=SENSOR_IMAGE)
    if not images:
        print(f"\n{Fore.RED}Error:{Style.RESET_ALL} Image '{SENSOR_IMAGE}' not found.")
        reporter.add_error(f"Sensor image '{SENSOR_IMAGE}' not found")
        return EXIT_FAIL

    def sample_platform_stats(samples=3, interval=10):
        """Collect docker stats for all services, return averaged results."""
        all_samples = []
        for i in range(samples):
            time.sleep(interval)
            stats_data = DockerOps.stats()
            # Filter to known services
            svc_stats = {}
            for s in stats_data:
                name = s.get("Name", "").lstrip("/")
                svc_stats[name] = {
                    "memory_mb": parse_memory_mb(s.get("MemUsage", "")),
                    "cpu_percent": parse_cpu_percent(s.get("CPUPerc", "")),
                }
            all_samples.append(svc_stats)

        # Average
        if not all_samples:
            return {"total_memory_mb": 0, "total_cpu_percent": 0, "services": {}}

        all_names = set()
        for s in all_samples:
            all_names.update(s.keys())

        avg = {}
        total_mem = 0.0
        total_cpu = 0.0
        for name in all_names:
            mems = [s.get(name, {}).get("memory_mb", 0) for s in all_samples]
            cpus = [s.get(name, {}).get("cpu_percent", 0) for s in all_samples]
            avg_mem = statistics.mean(mems)
            avg_cpu = statistics.mean(cpus)
            avg[name] = {"memory_mb": round(avg_mem, 1), "cpu_percent": round(avg_cpu, 3)}
            total_mem += avg_mem
            total_cpu += avg_cpu

        return {
            "total_memory_mb": round(total_mem, 1),
            "total_cpu_percent": round(total_cpu, 3),
            "services": avg,
            "sample_count": samples,
        }

    # ---- IDLE ----
    cleanup_bench_sensors()
    print(f"\n{Fore.YELLOW}Measuring IDLE state (waiting {args.stabilize}s for stabilization)...{Style.RESET_ALL}")
    time.sleep(args.stabilize)
    idle = sample_platform_stats(samples=args.samples, interval=args.sample_interval)
    print(f"  Platform memory: {idle['total_memory_mb']}MB, "
          f"CPU: {idle['total_cpu_percent']}%")

    # ---- LOADED ----
    print(f"\n{Fore.YELLOW}Deploying {args.sensors} sensor(s) for LOADED measurement...{Style.RESET_ALL}")
    sensor_ids = [bench_name("res", i + 1) for i in range(args.sensors)]

    # Quick deploy without MQTT tracking for resources
    for sid in sensor_ids:
        result = deploy_one_sensor(sid, profile="normal", interval=5)
        if not result.get("ok"):
            reporter.add_warning(f"Resource deploy failed for {sid}: {result.get('error')}")

    print(f"  Deployed, waiting {args.stabilize}s for stabilization...")
    time.sleep(args.stabilize)
    loaded = sample_platform_stats(samples=args.samples, interval=args.sample_interval)

    # Per-sensor memory
    bench_containers = DockerOps.list_containers(filter_name="bench_res_")
    bench_stats = DockerOps.stats([c["ID"] for c in bench_containers])
    sensor_mems = [parse_memory_mb(s.get("MemUsage", "")) for s in bench_stats]
    sensor_cpus = [parse_cpu_percent(s.get("CPUPerc", "")) for s in bench_stats]

    per_sensor_mem = (
        round(statistics.mean(sensor_mems), 1) if sensor_mems else 0
    )
    per_sensor_cpu = (
        round(statistics.mean(sensor_cpus), 4) if sensor_cpus else 0
    )
    memory_delta = round(loaded["total_memory_mb"] - idle["total_memory_mb"], 1)

    print(f"\n  Platform memory (loaded): {loaded['total_memory_mb']}MB")
    print(f"  Memory delta: {memory_delta}MB for {args.sensors} sensors")
    print(f"  Per sensor: {per_sensor_mem}MB, {per_sensor_cpu}% CPU")

    # Cleanup
    print(f"\n{Fore.YELLOW}Cleaning up...{Style.RESET_ALL}")
    cleanup_bench_sensors()

    reporter.set_result("resources", {
        "idle": {
            "sensor_count": 0,
            "platform_memory_mb": idle["total_memory_mb"],
            "platform_cpu_percent": idle["total_cpu_percent"],
            "sample_count": idle["sample_count"],
            "services": idle.get("services", {}),
        },
        "loaded": {
            "sensor_count": args.sensors,
            "platform_memory_mb": loaded["total_memory_mb"],
            "platform_cpu_percent": loaded["total_cpu_percent"],
            "per_sensor_memory_mb": per_sensor_mem,
            "per_sensor_cpu_percent": per_sensor_cpu,
            "memory_delta_mb": memory_delta,
            "memory_efficiency_mb_per_sensor": round(
                memory_delta / max(args.sensors, 1), 1
            ),
            "sample_count": loaded["sample_count"],
        },
    })

    return EXIT_OK


# ===================================================================
# COMMAND: all (full suite)
# ===================================================================
def cmd_all(args, reporter):
    """Run the full benchmark suite sequentially."""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f" IoT InfraLab -- Full Benchmark Suite")
    print(f"{'=' * 60}{Style.RESET_ALL}\n")

    # 1. Health
    print(f"{Fore.CYAN}─── Phase 1: Health Check ───{Style.RESET_ALL}")
    rc = cmd_health(args, reporter)
    if rc != EXIT_OK:
        print(f"\n{Fore.RED}Health check failed -- aborting suite.{Style.RESET_ALL}")
        return rc
    time.sleep(1)

    # 2. Resources (idle baseline before any sensors)
    print(f"\n{Fore.CYAN}─── Phase 2: Idle Resource Baseline ───{Style.RESET_ALL}")
    rc = cmd_resources(args, reporter)
    if rc != EXIT_OK:
        print(f"\n{Fore.YELLOW}Resource baseline had issues, continuing...{Style.RESET_ALL}")
    time.sleep(2)

    # 3. Startup timing (requires compose down + up)
    print(f"\n{Fore.CYAN}─── Phase 3: Startup Timing ───{Style.RESET_ALL}")
    # Don't take down if we just did resources (stack is up)
    args.skip_down = True
    rc = cmd_startup(args, reporter)
    time.sleep(2)

    # 4. Deploy lifecycle
    args.skip_down = True  # keep stack up
    print(f"\n{Fore.CYAN}─── Phase 4: Sensor Deployment Lifecycle ───{Style.RESET_ALL}")
    rc = cmd_deploy(args, reporter)
    time.sleep(2)

    # 5. Scaling
    print(f"\n{Fore.CYAN}─── Phase 5: Sensor Scaling ───{Style.RESET_ALL}")
    rc = cmd_scale(args, reporter)
    time.sleep(2)

    # 6. MQTT Latency
    print(f"\n{Fore.CYAN}─── Phase 6: MQTT Latency ───{Style.RESET_ALL}")
    rc = cmd_latency(args, reporter)
    time.sleep(1)

    # Write report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"benchmark_{timestamp}.json"
    reporter.to_json(report_path)
    csv_files = reporter.to_csv(REPORTS_DIR)

    print(f"\n{Fore.GREEN}{'=' * 60}")
    print(f" Full suite complete!")
    print(f"{'=' * 60}{Style.RESET_ALL}")
    print(f"  Report  : {report_path}")
    for csv_file in csv_files:
        print(f"  CSV     : {csv_file}")

    reporter.print_summary()
    return EXIT_OK


# ===================================================================
# COMMAND: report
# ===================================================================
def cmd_report(args, reporter):
    """Re-export a saved JSON report as CSV files."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"{Fore.RED}Error:{Style.RESET_ALL} Report not found: {input_path}")
        return EXIT_FAIL

    with open(input_path) as f:
        data = json.load(f)

    # Populate reporter with saved data
    reporter.results = data.get("results", {})
    reporter.warnings = data.get("warnings", [])
    reporter.errors = data.get("errors", [])

    output_dir = Path(args.output)
    csv_files = reporter.to_csv(output_dir)

    print(f"\nCSV exports ({len(csv_files)} files):")
    for path in csv_files:
        print(f"  {path}")

    # Print summary
    print(f"\nReport metadata:")
    meta = data.get("meta", {})
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            print(f"  {k}: {v}")

    return EXIT_OK


# ===================================================================
# Signal handler -- cleanup on Ctrl+C
# ===================================================================
_sigint_caught = False


def _handle_sigint(signum, frame):
    global _sigint_caught
    if _sigint_caught:
        print(f"\n{Fore.RED}Forcing exit...{Style.RESET_ALL}")
        sys.exit(130)
    _sigint_caught = True
    print(f"\n\n{Fore.YELLOW}Interrupted! Cleaning up benchmark sensors...{Style.RESET_ALL}")
    try:
        remaining = cleanup_bench_sensors()
        print(f"Cleaned up. ({remaining} remaining)")
    except Exception:
        pass
    print(f"Run: docker rm -f $(docker ps -aq --filter name=bench_)  # if any remain")
    sys.exit(130)


# ===================================================================
# main / argparse
# ===================================================================
def main():
    global BROKER_HOST
    signal.signal(signal.SIGINT, _handle_sigint)

    parser = argparse.ArgumentParser(
        description="IoT InfraLab -- Sensor Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Subcommands:\n"
            "  health          Pre-flight checks\n"
            "  startup         Stack startup timing\n"
            "  deploy          Sensor deployment lifecycle\n"
            "  scale           Scaling curve measurement\n"
            "  latency         MQTT latency / throughput\n"
            "  resources       Resource footprint (idle vs loaded)\n"
            "  all             Full benchmark suite\n"
            "  report          Re-export JSON report as CSV\n"
        ),
    )
    parser.add_argument(
        "--host", default=BROKER_HOST,
        help="Target host (default: localhost)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # health
    sub.add_parser("health", help="Pre-flight checks")

    # startup
    p_startup = sub.add_parser("startup", help="Startup timing")
    p_startup.add_argument(
        "--compose-file", type=str, default=str(COMPOSE_FILE),
        help=f"Compose file path",
    )
    p_startup.add_argument(
        "--timeout", type=int, default=120,
        help="Per-service timeout in seconds (default: 120)",
    )
    p_startup.add_argument(
        "--skip-down", action="store_true",
        help="Skip docker compose down (use current state)",
    )

    # deploy
    p_deploy = sub.add_parser("deploy", help="Sensor lifecycle timing")
    p_deploy.add_argument(
        "--count", type=int, default=5,
        help="Number of sensors to deploy (default: 5)",
    )
    p_deploy.add_argument(
        "--interval", type=int, default=5,
        help="Sensor publish interval in seconds (default: 5)",
    )
    p_deploy.add_argument(
        "--profile", choices=["normal", "failing", "erratic"],
        default="normal",
    )
    p_deploy.add_argument(
        "--types", type=str, default="temperature",
        help="Comma-separated sensor types (default: temperature)",
    )

    # scale
    p_scale = sub.add_parser("scale", help="Scaling curve")
    p_scale.add_argument(
        "--max", type=int, default=50,
        help="Maximum number of sensors (default: 50)",
    )
    p_scale.add_argument(
        "--step", type=int, default=5,
        help="Increment between load levels (default: 5)",
    )
    p_scale.add_argument(
        "--parallel", type=int, default=3,
        help="Concurrent deployments (default: 3)",
    )
    p_scale.add_argument(
        "--interval", type=int, default=5,
        help="Sensor publish interval (default: 5)",
    )
    p_scale.add_argument(
        "--profile", choices=["normal", "failing", "erratic"],
        default="normal",
    )
    p_scale.add_argument(
        "--types", type=str, default="temperature",
        help="Comma-separated sensor types (default: temperature)",
    )

    # latency
    p_lat = sub.add_parser("latency", help="MQTT latency/throughput")
    p_lat.add_argument(
        "--sensor-counts", type=str, default="1,5,10,20",
        help="Comma-separated load levels (default: 1,5,10,20)",
    )
    p_lat.add_argument(
        "--duration", type=int, default=30,
        help="Collection duration in seconds per level (default: 30)",
    )
    p_lat.add_argument(
        "--interval", type=int, default=5,
        help="Sensor publish interval (default: 5)",
    )
    p_lat.add_argument(
        "--profile", choices=["normal", "failing", "erratic"],
        default="normal",
    )
    p_lat.add_argument(
        "--types", type=str, default="temperature",
        help="Comma-separated sensor types (default: temperature)",
    )

    # resources
    p_res = sub.add_parser("resources", help="Resource footprint")
    p_res.add_argument(
        "--sensors", type=int, default=10,
        help="Number of sensors for loaded measurement (default: 10)",
    )
    p_res.add_argument(
        "--samples", type=int, default=3,
        help="Stats samples per state (default: 3)",
    )
    p_res.add_argument(
        "--sample-interval", type=int, default=10,
        help="Seconds between samples (default: 10)",
    )
    p_res.add_argument(
        "--stabilize", type=int, default=30,
        help="Stabilization wait in seconds (default: 30)",
    )

    # all (full suite)
    p_all = sub.add_parser("all", help="Full benchmark suite")
    _add_common_args(p_all)
    p_all.set_defaults(
        compose_file=str(COMPOSE_FILE),
        timeout=120,
        skip_down=True,
        max_sensors=20,
        step=5,
        parallel=3,
        duration=30,
        samples=3,
        sample_interval=10,
        stabilize=30,
        sensor_counts="1,5,10",
    )

    # report (re-export)
    p_report = sub.add_parser("report", help="Export report as CSV")
    p_report.add_argument(
        "--input", type=str,
        default=str(REPORTS_DIR / "benchmark_latest.json"),
        help="Input JSON report path",
    )
    p_report.add_argument(
        "--output", type=str,
        default=str(REPORTS_DIR),
        help="Output directory for CSV files",
    )

    args = parser.parse_args()

    # Override host from args
    BROKER_HOST = args.host

    reporter = Reporter(args)

    dispatch = {
        "health": cmd_health,
        "startup": cmd_startup,
        "deploy": cmd_deploy,
        "scale": cmd_scale,
        "latency": cmd_latency,
        "resources": cmd_resources,
        "all": cmd_all,
        "report": cmd_report,
    }

    fn = dispatch.get(args.command)
    if not fn:
        parser.print_help()
        return EXIT_USER_ERR

    try:
        rc = fn(args, reporter)
    except DockerOpsError as e:
        print(f"\n{Fore.RED}Docker error:{Style.RESET_ALL} {e}")
        reporter.add_error(f"Docker error: {e}")
        rc = EXIT_FAIL
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error:{Style.RESET_ALL} {e}")
        reporter.add_error(f"Unexpected: {e}")
        import traceback
        traceback.print_exc()
        rc = EXIT_FAIL

    # Auto-save report for non-report commands
    if args.command != "report" and reporter.results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"benchmark_{timestamp}.json"
        reporter.to_json(report_path)
        # Also save as latest
        latest_path = REPORTS_DIR / "benchmark_latest.json"
        reporter.to_json(latest_path)
        print(f"\n  Report: {report_path}")

        # Export CSVs
        csv_files = reporter.to_csv(REPORTS_DIR)
        for cf in csv_files:
            print(f"  CSV   : {cf}")

        reporter.print_summary()

    return rc


def _add_common_args(p):
    """Add common arguments shared across subcommands."""
    p.add_argument(
        "--count", type=int, default=5,
        help="Number of sensors to deploy per test",
    )
    p.add_argument(
        "--interval", type=int, default=5,
        help="Sensor publish interval",
    )
    p.add_argument(
        "--profile", choices=["normal", "failing", "erratic"],
        default="normal",
    )
    p.add_argument(
        "--types", type=str, default="temperature",
        help="Comma-separated sensor types",
    )


if __name__ == "__main__":
    sys.exit(main())
