"""Unit tests for attacker scripts' argument parsers.

Tests verify argparse configuration only — runtime behavior
(which requires MQTT broker) is not tested here.
"""

import os
import sys

import pytest

# Add project root and attacker dir to path so the scripts are importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_attacker_dir = os.path.join(_project_root, "src", "simulation", "docker_attacker")
for p in [_project_root, _attacker_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

import mqtt_inject
import mqtt_sniff
import mqtt_dos


class TestMqttInject:
    """mqtt_inject.py argument parsing."""

    def test_default_port(self):
        args = mqtt_inject.parser.parse_args(["--broker", "test.local"])
        assert args.port == 1883

    def test_custom_port(self):
        args = mqtt_inject.parser.parse_args(["--broker", "x", "--port", "8883"])
        assert args.port == 8883

    def test_broker_required(self):
        with pytest.raises(SystemExit):
            mqtt_inject.parser.parse_args([])

    def test_default_topic(self):
        args = mqtt_inject.parser.parse_args(["--broker", "x"])
        assert args.topic == "sensors/data"

    def test_custom_topic(self):
        args = mqtt_inject.parser.parse_args(["--broker", "x", "--topic", "my/topic"])
        assert args.topic == "my/topic"

    def test_default_value(self):
        args = mqtt_inject.parser.parse_args(["--broker", "x"])
        assert args.value == 9000

    def test_custom_value(self):
        args = mqtt_inject.parser.parse_args(["--broker", "x", "--value", "42"])
        assert args.value == 42


class TestMqttSniff:
    """mqtt_sniff.py argument parsing."""

    def test_broker_required(self):
        with pytest.raises(SystemExit):
            mqtt_sniff.parser.parse_args([])

    def test_default_port(self):
        args = mqtt_sniff.parser.parse_args(["--broker", "x"])
        assert args.port == 1883

    def test_custom_port(self):
        args = mqtt_sniff.parser.parse_args(["--broker", "x", "--port", "8883"])
        assert args.port == 8883

    def test_default_timeout(self):
        args = mqtt_sniff.parser.parse_args(["--broker", "x"])
        assert args.timeout == 10

    def test_custom_timeout(self):
        args = mqtt_sniff.parser.parse_args(["--broker", "x", "--timeout", "30"])
        assert args.timeout == 30


class TestMqttDos:
    """mqtt_dos.py argument parsing."""

    def test_broker_required(self):
        with pytest.raises(SystemExit):
            mqtt_dos.parser.parse_args([])

    def test_default_port(self):
        args = mqtt_dos.parser.parse_args(["--broker", "x"])
        assert args.port == 1883

    def test_default_threads(self):
        args = mqtt_dos.parser.parse_args(["--broker", "x"])
        assert args.threads == 50

    def test_custom_threads(self):
        args = mqtt_dos.parser.parse_args(["--broker", "x", "--threads", "10"])
        assert args.threads == 10
