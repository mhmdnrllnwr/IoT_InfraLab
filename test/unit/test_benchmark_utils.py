"""Unit tests for utility functions in test/benchmark_sensors.py.

Tests cover: Timer, parse_memory_mb, parse_cpu_percent,
validate_sensor_payload, bench_name, is_bench_container.
"""

import os
import sys
import time

import pytest

# Ensure project root is on sys.path so test/benchmark_sensors.py is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# Also ensure test/ is importable
_test_dir = os.path.join(_project_root, "test")
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from benchmark_sensors import (
    Timer,
    parse_memory_mb,
    parse_cpu_percent,
    validate_sensor_payload,
    bench_name,
    is_bench_container,
)


# =========================================================================
# Timer
# =========================================================================

class TestTimer:
    """Context manager with microsecond-precision timing."""

    def test_elapsed_is_positive_after_sleep(self):
        """Timer.elapsed is > 0 after a measurable sleep."""
        t = Timer()
        t.__enter__()
        time.sleep(0.01)
        t.__exit__(None, None, None)
        assert t.elapsed > 0

    def test_elapsed_roughly_matches_sleep(self):
        """Timer.elapsed approximately equals sleeptime (within 20ms tolerance)."""
        t = Timer()
        t.__enter__()
        time.sleep(0.05)
        t.__exit__(None, None, None)
        assert 40.0 <= t.elapsed <= 200.0  # 40-200ms tolerance

    def test_context_manager_syntax(self):
        """Timer works as a context manager."""
        with Timer() as t:
            time.sleep(0.01)
        assert t.elapsed > 0

    def test_elapsed_seconds_property(self):
        """elapsed_sec returns elapsed in seconds."""
        with Timer() as t:
            time.sleep(0.05)
        assert 0.04 <= t.elapsed_sec <= 0.2

    def test_zero_elapsed_without_sleep(self):
        """Almost-zero elapsed time when no work is done (sub-ms)."""
        with Timer() as t:
            pass
        assert t.elapsed < 10.0  # should be <10ms

    def test_reuse(self):
        """Timer can be reused — second reading is independent."""
        t = Timer()
        with t:
            time.sleep(0.01)
        first = t.elapsed
        with t:
            time.sleep(0.02)
        assert t.elapsed != first
        assert t.elapsed > first


# =========================================================================
# parse_memory_mb
# =========================================================================

class TestParseMemoryMB:
    """Parse docker stats memory strings to MB."""

    @pytest.mark.parametrize("input_str,expected", [
        ("15.2MiB / 256MiB", 15.2),
        ("0MiB / 64MiB", 0.0),
        ("100.5MiB / 128MiB", 100.5),
        ("256MiB / 512MiB", 256.0),
    ])
    def test_mib(self, input_str, expected):
        assert parse_memory_mb(input_str) == expected

    @pytest.mark.parametrize("input_str,expected", [
        ("1.5GiB / 4GiB", 1536.0),
        ("0.5GiB / 1GiB", 512.0),
        ("2GiB / 4GiB", 2048.0),
    ])
    def test_gib(self, input_str, expected):
        assert parse_memory_mb(input_str) == expected

    def test_kib(self):
        """KiB values convert correctly to MB."""
        result = parse_memory_mb("512KiB / 1GiB")
        assert result == pytest.approx(0.5, rel=0.01)

    def test_mb_unit(self):
        """MB (decimal) values pass through unchanged."""
        result = parse_memory_mb("120.5MB / 1.2GB")
        assert result == 120.5

    def test_gb_unit(self):
        """GB (decimal) values convert: 1 GB = 1000 MB."""
        result = parse_memory_mb("1.5GB / 2GB")
        assert result == 1500.0

    def test_empty_string(self):
        assert parse_memory_mb("") == 0.0

    def test_none_returns_zero(self):
        """None input returns 0.0 without raising."""
        assert parse_memory_mb(None) == 0.0

    def test_malformed_string(self):
        """Malformed input returns 0.0 without crashing."""
        assert parse_memory_mb("not a memory value") == 0.0

    def test_b_unit(self):
        """Plain 'B' suffix treats as bytes -> MB."""
        result = parse_memory_mb("1048576B / 1GB")
        assert result == pytest.approx(1.0, rel=0.1)

    def test_no_unit(self):
        """Bare number returns it as-is."""
        result = parse_memory_mb("42")
        assert result == 42.0

    def test_percent_sign_suffix(self):
        """Strings with % in used part (non-standard) fall back to 0."""
        result = parse_memory_mb("50% / 256MiB")
        # "50%" is not parseable as a number, returns 0.0
        assert result == 0.0


# =========================================================================
# parse_cpu_percent
# =========================================================================

class TestParseCPUPercent:
    """Parse docker stats CPU percentage strings."""

    @pytest.mark.parametrize("input_str,expected", [
        ("0.25%", 0.25),
        ("2.50%", 2.5),
        ("100.00%", 100.0),
        ("0.00%", 0.0),
    ])
    def test_standard(self, input_str, expected):
        assert parse_cpu_percent(input_str) == expected

    def test_empty_string(self):
        assert parse_cpu_percent("") == 0.0

    def test_no_percent_sign(self):
        """String without % still works."""
        assert parse_cpu_percent("0.5") == 0.5


# =========================================================================
# validate_sensor_payload
# =========================================================================

class TestValidateSensorPayload:
    """Check sensor MQTT payload structure."""

    def test_valid_full_payload(self):
        """All required fields present and correct types."""
        payload = {
            "sensor_id": "test_1",
            "profile": "normal",
            "readings": {"temperature": 25.5},
            "timestamp": 1234567890.0,
        }
        assert validate_sensor_payload(payload) is True

    def test_missing_sensor_id(self):
        payload = {"readings": {}, "timestamp": 1.0}
        assert validate_sensor_payload(payload) is False

    def test_missing_readings(self):
        payload = {"sensor_id": "x", "timestamp": 1.0}
        assert validate_sensor_payload(payload) is False

    def test_missing_timestamp(self):
        payload = {"sensor_id": "x", "readings": {}}
        assert validate_sensor_payload(payload) is False

    def test_readings_not_a_dict(self):
        payload = {"sensor_id": "x", "readings": "not_a_dict", "timestamp": 1.0}
        assert validate_sensor_payload(payload) is False

    def test_readings_empty_dict(self):
        """Empty readings dict is structurally valid (no data, but correct shape)."""
        payload = {"sensor_id": "x", "readings": {}, "timestamp": 1.0}
        assert validate_sensor_payload(payload) is True

    def test_none_payload(self):
        assert validate_sensor_payload(None) is False

    def test_non_dict_payload(self):
        assert validate_sensor_payload("string") is False
        assert validate_sensor_payload(42) is False
        assert validate_sensor_payload([]) is False

    def test_extra_fields_ignored(self):
        """Extra fields beyond required ones are allowed."""
        payload = {
            "sensor_id": "x",
            "readings": {"t": 1},
            "timestamp": 1.0,
            "extra_field": "ignored",
        }
        assert validate_sensor_payload(payload) is True


# =========================================================================
# bench_name & is_bench_container
# =========================================================================

class TestBenchNaming:
    """Sensor naming conventions."""

    @pytest.mark.parametrize("cmd,n,expected", [
        ("deploy", 1, "bench_deploy_1"),
        ("scale", 10, "bench_scale_10"),
        ("lat", 99, "bench_lat_99"),
        ("res", 0, "bench_res_0"),
    ])
    def test_bench_name(self, cmd, n, expected):
        assert bench_name(cmd, n) == expected

    @pytest.mark.parametrize("name,expected", [
        ("bench_deploy_1", True),
        ("bench_scale_5", True),
        ("bench_xxx", True),
        ("sensor_A", False),
        ("iot-sensor", False),
        ("", False),
        (None, False),
    ])
    def test_is_bench_container(self, name, expected):
        result = is_bench_container(name)
        if expected:
            assert result, f"Expected truthy for {name!r}, got {result!r}"
        else:
            assert not result, f"Expected falsy for {name!r}, got {result!r}"
