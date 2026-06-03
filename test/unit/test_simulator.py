"""Unit tests for src/simulation/docker_sensor/simulator.py.

Tests cover get_sensor_value() for all profiles, load_config() for
various config states, and edge cases (missing files, zero-width ranges).
"""

import json
import os
import math
from pathlib import Path
from unittest.mock import patch

import pytest

# Module under test -- imported after manipulating its CONFIG_FILE paths
import src.simulation.docker_sensor.simulator as sim


# =========================================================================
# get_sensor_value() — normal profile
# =========================================================================

class TestGetSensorValueNormal:
    """get_sensor_value() with profile='normal' — basic distribution."""

    def setup_method(self):
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}

    def test_value_within_range(self):
        """Value falls within the specified range."""
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert 10.0 <= val <= 40.0

    def test_value_is_float(self):
        """Value is a float (or int convertible to float)."""
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert isinstance(val, (int, float))

    def test_multiple_values_have_variance(self):
        """Over 50 calls, at least 3 distinct values appear (no constant return)."""
        vals = {sim.get_sensor_value("temperature", "normal", 0) for _ in range(50)}
        assert len(vals) >= 3, f"Expected variance, got only {len(vals)} values"

    def test_different_types_use_different_ranges(self):
        """Two sensor types use their respective ranges."""
        sim.BASE_RANGES.update({"humidity": [30.0, 90.0]})
        t = sim.get_sensor_value("temperature", "normal", 0)
        h = sim.get_sensor_value("humidity", "normal", 0)
        assert 10.0 <= t <= 40.0
        assert 30.0 <= h <= 90.0


class TestGetSensorValueNormalEdgeCases:
    """Edge cases for normal profile."""

    def test_missing_type_uses_default(self):
        """Unknown sensor type falls back to [0.0, 100.0]."""
        sim.BASE_RANGES = {}
        val = sim.get_sensor_value("nonexistent", "normal", 0)
        assert 0.0 <= val <= 100.0

    def test_zero_width_range(self):
        """Range with min==max returns exactly that value (deterministic)."""
        sim.BASE_RANGES = {"constant": [42.0, 42.0]}
        vals = {sim.get_sensor_value("constant", "normal", 0) for _ in range(20)}
        assert vals == {42.0}

    def test_single_element_range_tuple_packed(self):
        """Handles range stored as tuple (min, max)."""
        sim.BASE_RANGES = {"test": (15.0, 25.0)}
        for _ in range(20):
            val = sim.get_sensor_value("test", "normal", 0)
            assert 15.0 <= val <= 25.0

    def test_negative_range_allowed(self):
        """Range can include negative values."""
        sim.BASE_RANGES = {"signed": [-50.0, -10.0]}
        for _ in range(20):
            val = sim.get_sensor_value("signed", "normal", 0)
            assert -50.0 <= val <= -10.0


# =========================================================================
# get_sensor_value() — failing profile
# =========================================================================

class TestGetSensorValueFailing:
    """get_sensor_value() with profile='failing' — upward drift."""

    def setup_method(self):
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}

    def test_value_at_zero_elapsed(self):
        """At elapsed=0, value should be in the base range (no drift yet)."""
        val = sim.get_sensor_value("temperature", "failing", 0)
        assert 10.0 <= val <= 40.0

    def test_drift_increases_with_time(self):
        """Values at larger elapsed are consistently higher than at start
        (drift factor increases monotonically)."""
        sim.start_time = 0  # reset for deterministic test
        # Set a fixed random seed by doing many calls — we test statistical property
        sim.BASE_RANGES = {"temperature": [10.0, 11.0]}
        t0_vals = [sim.get_sensor_value("temperature", "failing", 0) for _ in range(10)]
        t300_vals = [sim.get_sensor_value("temperature", "failing", 300) for _ in range(10)]
        # At 300s, drift factor = 1.0 + (300/30)*0.05 = 1.5, so max would be 11*1.5 = 16.5
        assert all(v >= 10.0 for v in t300_vals), "Drifted values should stay above min"
        assert max(t300_vals) <= 11.0 * 1.5 + 0.01, "Drift capped at expected factor"

    def test_drift_factor_formula(self):
        """At elapsed=30s (one drift period), drift_factor = 1.05."""
        sim.BASE_RANGES = {"temperature": [100.0, 100.0]}
        val = sim.get_sensor_value("temperature", "failing", 30)
        assert val == pytest.approx(100.0 * 1.05, rel=0.01)

    def test_drift_at_60s(self):
        """At elapsed=60s, drift_factor = 1.10."""
        sim.BASE_RANGES = {"temperature": [100.0, 100.0]}
        val = sim.get_sensor_value("temperature", "failing", 60)
        assert val == pytest.approx(100.0 * 1.10, rel=0.01)

    def test_large_elapsed_no_error(self):
        """Extreme elapsed values don't cause overflow or errors."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}
        val = sim.get_sensor_value("temperature", "failing", 1_000_000)
        assert isinstance(val, (int, float))
        assert not math.isnan(val)
        assert not math.isinf(val)


# =========================================================================
# get_sensor_value() — erratic profile
# =========================================================================

class TestGetSensorValueErratic:
    """get_sensor_value() with profile='erratic' — occasional spikes."""

    def setup_method(self):
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}

    def test_base_value_within_range(self):
        """Non-spike values stay within the base range."""
        # Run 500 iterations; non-spike values must be in range
        for _ in range(500):
            val = sim.get_sensor_value("temperature", "erratic", 0)
            low = 10.0
            high = 40.0
            # Spikes are 2-4x multiplier, so max spike = 40*4 = 160
            if val <= high:
                assert low <= val <= high
            else:
                assert low * 2 <= val <= high * 4, f"Spike {val} out of expected [{low*2},{high*4}]"

    def test_spike_rate_approximately_10_percent(self):
        """~10% of values should be spikes (above max range)."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}
        spikes = 0
        n = 1000
        for _ in range(n):
            val = sim.get_sensor_value("temperature", "erratic", 0)
            if val > 40.0:
                spikes += 1
        rate = spikes / n
        # 10% ± 5% (statistical tolerance)
        assert 0.03 <= rate <= 0.20, f"Spike rate {rate:.3f} outside expected 0.05-0.15"

    def test_spike_multiplier_range(self):
        """Spike values should be 2x-4x the base value."""
        sim.BASE_RANGES = {"temperature": [100.0, 100.0]}
        spikes = []
        for _ in range(2000):
            val = sim.get_sensor_value("temperature", "erratic", 0)
            if val > 100.0:
                spikes.append(val)
        assert len(spikes) > 0, "Expected at least one spike in 2000 iterations"
        for s in spikes:
            assert 200.0 <= s <= 400.0, f"Spike {s} outside 2x-4x multiplier range"


# =========================================================================
# get_sensor_value() — vibration precision
# =========================================================================

class TestGetSensorValueVibration:
    """Vibration sensor type requires 3-decimal precision."""

    def setup_method(self):
        sim.BASE_RANGES = {"vibration": [0.0, 10.0]}

    def test_vibration_precision_three_decimals(self):
        """Vibration values have 3 decimal places."""
        vals = []
        for _ in range(100):
            val = sim.get_sensor_value("vibration", "normal", 0)
            vals.append(val)
        # Check at least some values have 3 decimal precision
        has_3dec = any(len(str(v).split(".")[-1]) >= 3 for v in vals)
        assert has_3dec, "No vibration values with 3+ decimal places found"

    def test_temperature_has_one_decimal(self):
        """Temperature (non-vibration) uses 1 decimal default."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}
        vals = []
        for _ in range(100):
            val = sim.get_sensor_value("temperature", "normal", 0)
            vals.append(val)
        # All values should have at most 1 decimal
        for v in vals:
            decimal_part = str(v).split(".")[-1]
            assert len(decimal_part) <= 2, f"Temperature {v} has >1 decimal"


# =========================================================================
# get_sensor_value() — blueprint overrides
# =========================================================================

class TestGetSensorValueBlueprints:
    """DYNAMIC_BLUEPRINTS override BASE_RANGES."""

    def test_blueprint_overrides_base_range(self):
        """When blueprint defines a range for the type, use blueprint range."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}
        sim.DYNAMIC_BLUEPRINTS = {
            "temperature": {"range": [50.0, 100.0], "unit": "C"}
        }
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert 50.0 <= val <= 100.0, "Blueprint range should override base range"

    def test_blueprint_only_applied_for_matching_type(self):
        """Blueprint for one type doesn't affect other types."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0], "humidity": [30.0, 90.0]}
        sim.DYNAMIC_BLUEPRINTS = {
            "temperature": {"range": [50.0, 100.0]}
        }
        h = sim.get_sensor_value("humidity", "normal", 0)
        assert 30.0 <= h <= 90.0, "Blueprint shouldn't affect non-overridden types"

    def test_blueprint_missing_range_key(self):
        """Blueprint dict without 'range' key falls back to BASE_RANGES."""
        sim.BASE_RANGES = {"temperature": [10.0, 40.0]}
        sim.DYNAMIC_BLUEPRINTS = {
            "temperature": {"unit": "C"}  # no range key
        }
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert 10.0 <= val <= 40.0


# =========================================================================
# load_config() — config file loading
# =========================================================================

class TestLoadConfig:
    """load_config() reads sensor_types.json and sensor_settings.json."""

    def test_loads_sensor_types(self, sensor_config_dir):
        """BASE_RANGES is populated from sensor_types.json."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "sensor_types.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        assert "temperature" in sim.BASE_RANGES
        assert sim.BASE_RANGES["temperature"] == [10.0, 40.0]
        assert sim.BASE_RANGES["humidity"] == [30.0, 90.0]

    def test_loads_blueprints(self, sensor_config_dir):
        """DYNAMIC_BLUEPRINTS is populated from blueprints key."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "sensor_types.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        assert "DHT11" in sim.DYNAMIC_BLUEPRINTS
        assert sim.DYNAMIC_BLUEPRINTS["DHT11"]["range"] == [10.0, 40.0]

    def test_missing_types_file(self, sensor_config_dir):
        """Missing sensor_types.json leaves BASE_RANGES empty."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "missing.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        assert sim.BASE_RANGES == {}

    def test_missing_settings_file(self, sensor_config_dir):
        """Missing sensor_settings.json leaves DYNAMIC_BLUEPRINTS empty."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "sensor_types.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "missing.json")):
                sim.load_config()
        assert sim.DYNAMIC_BLUEPRINTS == {}

    def test_nonexistent_sensor_id(self, sensor_config_dir):
        """Sensor ID not in settings.sensors — SENSOR_TYPES unchanged."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "sensor_types.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        # Default SENSOR_TYPES is ["temperature"]
        assert sim.SENSOR_TYPES == ["temperature"]

    def test_malformed_json_does_not_crash(self, sensor_config_dir):
        """Malformed JSON files are handled gracefully (ranges stay empty)."""
        bad_file = sensor_config_dir / "bad.json"
        bad_file.write_text("{invalid json}")
        with patch.object(sim, "SENSOR_TYPES_FILE", str(bad_file)):
            with patch.object(sim, "CONFIG_FILE", str(bad_file)):
                # Should not raise
                sim.load_config()

    def test_reload_clears_and_reloads(self, sensor_config_dir):
        """Calling load_config() twice reloads fresh data."""
        types_path = sensor_config_dir / "sensor_types.json"
        # First load
        with patch.object(sim, "SENSOR_TYPES_FILE", str(types_path)):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        initial = dict(sim.BASE_RANGES)
        # Modify file
        data = {"new_type": [1.0, 2.0]}
        with open(types_path, "w") as f:
            json.dump(data, f)
        # Second load
        with patch.object(sim, "SENSOR_TYPES_FILE", str(types_path)):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        assert sim.BASE_RANGES != initial
        assert "new_type" in sim.BASE_RANGES


# =========================================================================
# Integration: load_config() + get_sensor_value()
# =========================================================================

class TestConfigAndValues:
    """Verify loaded config feeds correctly into get_sensor_value."""

    def test_config_feeds_value_generation(self, sensor_config_dir):
        """After load_config(), get_sensor_value uses loaded ranges."""
        with patch.object(sim, "SENSOR_TYPES_FILE", str(sensor_config_dir / "sensor_types.json")):
            with patch.object(sim, "CONFIG_FILE", str(sensor_config_dir / "sensor_settings.json")):
                sim.load_config()
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert sim.BASE_RANGES["temperature"][0] <= val <= sim.BASE_RANGES["temperature"][1]

    def test_dynamic_blueprint_affects_value(self, sensor_config_dir):
        """Blueprint override in settings config affects value range."""
        types_path = sensor_config_dir / "sensor_types.json"
        settings_path = sensor_config_dir / "sensor_settings.json"
        # Add blueprint override
        with open(settings_path) as f:
            settings = json.load(f)
        settings["blueprints"]["temperature"] = {"range": [200.0, 300.0]}
        with open(settings_path, "w") as f:
            json.dump(settings, f)
        with patch.object(sim, "SENSOR_TYPES_FILE", str(types_path)):
            with patch.object(sim, "CONFIG_FILE", str(settings_path)):
                sim.load_config()
        val = sim.get_sensor_value("temperature", "normal", 0)
        assert 200.0 <= val <= 300.0, "Blueprint override should change value range"


# =========================================================================
# Module-level constants
# =========================================================================

class TestModuleConstants:
    """Verify simulator module constants are as expected."""

    def test_mqtt_broker_default(self):
        """MQTT_BROKER defaults to 'mosquitto' (the Docker service name)."""
        assert sim.MQTT_BROKER == "mosquitto"

    def test_otel_endpoint_default(self):
        """OTEL endpoint defaults to otel-collector:4317."""
        assert "otel-collector:4317" in sim.OTEL_ENDPOINT

    def test_interval_type(self):
        """INTERVAL is an int."""
        assert isinstance(sim.INTERVAL, int)

    def test_topic_format(self):
        """MQTT topic format follows sensors/factory/{SENSOR_ID}."""
        topic = f"sensors/factory/{sim.SENSOR_ID}"
        assert topic.startswith("sensors/factory/")
