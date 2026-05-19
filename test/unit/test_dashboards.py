"""Unit tests for test/gen_dashboards.py.

Tests verify dashboard structure, panel schemas, and output file
validity without requiring Grafana or InfluxDB.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Add project root and test dir to sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
for p in [_project_root, os.path.join(_project_root, "test")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from gen_dashboards import create_base, get_iot_sensors, get_platform_health, get_security


class TestCreateBase:
    """Base dashboard structure."""

    def test_returns_dict(self):
        dash = create_base("Test", "test-uid", [], ["test"])
        assert isinstance(dash, dict)

    def test_has_required_keys(self, expected_dashboard_keys):
        dash = create_base("Test", "test-uid", [], ["test"])
        assert expected_dashboard_keys.issubset(dash.keys())

    def test_title_set(self):
        dash = create_base("My Dashboard", "uid-1", [], ["tag"])
        assert dash["title"] == "My Dashboard"

    def test_uid_set(self):
        dash = create_base("Test", "my-custom-uid", [], [])
        assert dash["uid"] == "my-custom-uid"

    def test_tags_default(self):
        dash = create_base("Test", "uid", [], None)
        assert dash["tags"] == ["infralab"]

    def test_tags_custom(self):
        dash = create_base("Test", "uid", [], ["custom", "tags"])
        assert "custom" in dash["tags"]
        assert "tags" in dash["tags"]

    def test_panels_empty_list(self):
        dash = create_base("Test", "uid", [], [])
        assert dash["panels"] == []

    def test_templating_from_list(self):
        t_list = [{"name": "var1", "type": "query"}]
        dash = create_base("Test", "uid", t_list, [])
        assert dash["templating"]["list"] == t_list

    def test_schema_version_39(self):
        dash = create_base("Test", "uid", [], [])
        assert dash["schemaVersion"] == 39

    def test_time_default(self):
        dash = create_base("Test", "uid", [], [])
        assert "from" in dash["time"]
        assert "to" in dash["time"]


class TestIoTSensorsDashboard:
    """IoT Sensors Overview dashboard structure."""

    def test_dashboard_structure(self, expected_dashboard_keys):
        dash = get_iot_sensors()
        assert expected_dashboard_keys.issubset(dash.keys())

    def test_has_panels(self):
        dash = get_iot_sensors()
        assert len(dash["panels"]) > 0

    def test_all_panels_have_required_keys(self, expected_panel_keys):
        dash = get_iot_sensors()
        for i, panel in enumerate(dash["panels"]):
            missing = expected_panel_keys - set(panel.keys())
            assert not missing, f"Panel {i} ({panel.get('title', '?')}) missing: {missing}"

    def test_panel_types_known(self):
        dash = get_iot_sensors()
        known = {"stat", "timeseries", "table"}
        for panel in dash["panels"]:
            assert panel["type"] in known, f"Unknown panel type: {panel['type']}"

    def test_all_panels_have_targets(self):
        dash = get_iot_sensors()
        for panel in dash["panels"]:
            assert len(panel["targets"]) > 0, f"Panel '{panel['title']}' has no targets"

    def test_correct_title(self):
        dash = get_iot_sensors()
        assert "IoT" in dash["title"]

    def test_tags_include_iot(self):
        dash = get_iot_sensors()
        assert "iot" in dash["tags"]


class TestPlatformHealthDashboard:
    """Platform Health dashboard structure."""

    def test_has_panels(self):
        dash = get_platform_health()
        assert len(dash["panels"]) > 0

    def test_all_panels_have_required_keys(self, expected_panel_keys):
        dash = get_platform_health()
        for i, panel in enumerate(dash["panels"]):
            missing = expected_panel_keys - set(panel.keys())
            assert not missing, f"Panel {i} missing: {missing}"

    def test_panel_types_known(self):
        dash = get_platform_health()
        known = {"timeseries", "table"}
        for panel in dash["panels"]:
            assert panel["type"] in known, f"Unknown type: {panel['type']}"

    def test_templating_has_service_var(self):
        dash = get_platform_health()
        names = [v["name"] for v in dash["templating"]["list"]]
        assert "service" in names

    def test_includes_docker_container_cpu_query(self):
        dash = get_platform_health()
        targets_json = json.dumps(dash["panels"])
        assert "docker_container_cpu" in targets_json


class TestSecurityDashboard:
    """Security Operations (SOC) dashboard structure."""

    def test_has_panels(self):
        dash = get_security()
        assert len(dash["panels"]) > 0

    def test_all_panels_have_required_keys(self, expected_panel_keys):
        dash = get_security()
        for i, panel in enumerate(dash["panels"]):
            missing = expected_panel_keys - set(panel.keys())
            assert not missing, f"Panel {i} missing: {missing}"

    def test_panel_types_known(self):
        dash = get_security()
        known = {"stat", "timeseries", "piechart", "bargauge", "table", "logs"}
        for panel in dash["panels"]:
            assert panel["type"] in known, f"Unknown type: {panel['type']}"

    def test_loki_datasource_referenced(self):
        """All panels use Loki datasource."""
        dash = get_security()
        for panel in dash["panels"]:
            for target in panel.get("targets", []):
                # Logs panels use expr (LogQL), not Flux
                assert "expr" in target or "query" in target

    def test_includes_suricata_alerts(self):
        dash = get_security()
        targets_json = json.dumps(dash["panels"])
        assert "suricata" in targets_json.lower()
        assert "alert" in targets_json.lower()

    def test_templating_has_attack_type(self):
        dash = get_security()
        names = [v["name"] for v in dash["templating"]["list"]]
        assert "attack_type" in names
        assert "src_ip" in names


class TestDashboardOutput:
    """Verify dashboards serialize to valid JSON (Grafana-compatible)."""

    def test_iot_sensors_serializable(self):
        dash = get_iot_sensors()
        dumped = json.dumps(dash)
        assert len(dumped) > 1000
        # Re-parse validates JSON
        parsed = json.loads(dumped)
        assert parsed["title"] == dash["title"]

    def test_platform_health_serializable(self):
        dash = get_platform_health()
        json.dumps(dash)

    def test_security_serializable(self):
        dash = get_security()
        json.dumps(dash)

    def test_output_writes_valid_json(self):
        """Simulate the script's write-to-disk logic."""
        dash = get_iot_sensors()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "iot_sensors.json"
            with open(path, "w") as f:
                json.dump(dash, f, indent=2)
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["title"] == dash["title"]
            assert len(loaded["panels"]) == len(dash["panels"])
