"""Shared pytest fixtures for IoT InfraLab unit tests."""

import json
import os
import tempfile
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Sensor config fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_sensor_types():
    """Standard sensor_types.json content as used by simulator.py."""
    return {
        "temperature": [10.0, 40.0],
        "humidity": [30.0, 90.0],
        "pressure": [950.0, 1050.0],
        "vibration": [0.0, 10.0],
        "power_consumption": [50.0, 500.0],
    }


@pytest.fixture
def sample_sensor_settings():
    """sensor_settings.json content with blueprints and overrides."""
    return {
        "blueprints": {
            "DHT11": {"range": [10.0, 40.0], "unit": "C", "description": "Temperature sensor"},
            "DHT22": {"range": [30.0, 90.0], "unit": "%", "description": "Humidity sensor"},
        },
        "sensors": {
            "sensor_overridden": {
                "types": "humidity,pressure",
            }
        },
    }


@pytest.fixture
def sensor_config_dir(sample_sensor_types, sample_sensor_settings):
    """Create a temp directory with both config files, return path."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        types_path = tmp / "sensor_types.json"
        settings_path = tmp / "sensor_settings.json"
        with open(types_path, "w") as f:
            json.dump(sample_sensor_types, f)
        with open(settings_path, "w") as f:
            json.dump(sample_sensor_settings, f)
        yield tmp


# ---------------------------------------------------------------------------
# Dashboard fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def expected_dashboard_keys():
    """Keys required in every Grafana dashboard JSON."""
    return {"title", "uid", "tags", "schemaVersion", "panels", "templating", "time"}


@pytest.fixture
def expected_panel_keys():
    """Keys required in every panel."""
    return {"type", "title", "gridPos", "targets"}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clear_simulator_globals():
    """Reset simulator module-level globals between tests."""
    import src.simulation.docker_sensor.simulator as sim

    sim.DYNAMIC_BLUEPRINTS = {}
    sim.BASE_RANGES = {}
    # Reset sensor types to default
    sim.SENSOR_TYPES = ["temperature"]
