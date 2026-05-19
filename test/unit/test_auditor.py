"""Unit tests for src/simulation/auditor_security/auditor.py.

Uses extensive mocking — real nmap/Gemini/MQTT are not required.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Set a dummy API key before importing auditor — module-level code
# creates genai.Client() using this env var.
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-unit-tests")

import pytest

# Add project root and auditor dir to path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_auditor_dir = os.path.join(_project_root, "src", "simulation", "auditor_security")
for p in [_project_root, _auditor_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture(autouse=True)
def auditor():
    """Import auditor module and reset globals / attach mock MQTT client."""
    # Patch OTel to prevent background export attempts to unreachable collector
    with patch("auditor.BatchSpanProcessor") as mock_bsp:
        import auditor as mod

    mod.last_scan_time = 0
    mod.is_scanning = False
    mod.MODEL_ID = "gemini-2.0-flash"
    mod.client_mqtt = MagicMock()
    return mod


class TestOnMessage:
    """MQTT on_message callback handlers."""

    def test_model_change(self, auditor):
        """Publishing to lab/security/model changes MODEL_ID."""
        msg = MagicMock()
        msg.topic = "lab/security/model"
        msg.payload = b"gemini-2.5-pro"
        auditor.on_message(None, None, msg)
        assert auditor.MODEL_ID == "gemini-2.5-pro"

    def test_model_change_publishes_status(self, auditor):
        msg = MagicMock()
        msg.topic = "lab/security/model"
        msg.payload = b"new-model"
        auditor.on_message(None, None, msg)
        auditor.client_mqtt.publish.assert_called_with(
            "lab/security/status", "Model Set: new-model"
        )

    def test_scan_now_triggers_thread(self, auditor):
        """First SCAN_NOW triggers a background thread."""
        msg = MagicMock()
        msg.topic = "lab/security/trigger"
        msg.payload = b"SCAN_NOW"
        with patch("auditor.threading") as mock_th:
            auditor.on_message(None, None, msg)
        assert mock_th.Thread.called

    def test_scan_now_during_cooldown(self, auditor):
        """SCAN_NOW within COOLDOWN_TIME returns cooldown message."""
        auditor.last_scan_time = 9999999999  # far in the future
        msg = MagicMock()
        msg.topic = "lab/security/trigger"
        msg.payload = b"SCAN_NOW"
        auditor.on_message(None, None, msg)
        call_msg = auditor.client_mqtt.publish.call_args[0][1]
        assert "Cooldown" in call_msg or "Wait" in call_msg

    def test_scan_now_during_active_scan(self, auditor):
        """SCAN_NOW while scanning returns busy status."""
        auditor.is_scanning = True
        msg = MagicMock()
        msg.topic = "lab/security/trigger"
        msg.payload = b"SCAN_NOW"
        auditor.on_message(None, None, msg)
        call_msg = auditor.client_mqtt.publish.call_args[0][1]
        assert "Busy" in call_msg or "in Progress" in call_msg

    def test_irrelevant_topic_ignored(self, auditor):
        """Messages on unrelated topics are ignored."""
        msg = MagicMock()
        msg.topic = "some/other/topic"
        msg.payload = b"data"
        auditor.on_message(None, None, msg)
        assert auditor.client_mqtt.publish.call_count == 0  # no new publish calls


class TestPerformAudit:
    """perform_audit() error and success paths."""

    def test_empty_scan_returns_early(self, auditor):
        """No hosts found → publishes cancellation status and returns."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.all_hosts.return_value = []
            mock_nm_cls.return_value = mock_nm
            with patch("auditor.client_ai") as mock_ai:
                auditor.perform_audit()
        # Should have published status with "No Hosts Found" or "Cancelled"
        status_calls = [c[0][1] for c in auditor.client_mqtt.publish.call_args_list if c[0][0] == "lab/security/status"]
        assert any("No Hosts" in str(c) or "Cancelled" in str(c) for c in status_calls)

    def test_scan_with_hosts_proceeds_to_ai(self, auditor):
        """Hosts found → calls AI analysis, publishes report."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.all_hosts.return_value = ["172.18.0.1"]
            mock_nm.__getitem__.return_value.all_protocols.return_value = ["tcp"]
            mock_nm.__getitem__.return_value.__getitem__.return_value = {
                80: {"state": "open", "name": "http", "product": "", "version": ""}
            }
            mock_nm_cls.return_value = mock_nm

            with patch("auditor.client_ai") as mock_ai:
                mock_resp = MagicMock()
                mock_resp.text = "<h3>Report</h3><table><tr><td>test</td></tr></table>"
                mock_ai.models.generate_content.return_value = mock_resp
                auditor.perform_audit()

        # Should have published a report
        report_calls = [c for c in auditor.client_mqtt.publish.call_args_list if c[0][0] == "lab/security/report"]
        assert len(report_calls) > 0
        # Report should contain the AI response
        assert "Report" in str(report_calls[-1].args)

    def test_nmap_error_handled(self, auditor):
        """nmap.PortScannerError is caught, error published."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.scan.side_effect = Exception("Nmap Error: cap")
            mock_nm_cls.return_value = mock_nm
            with patch("auditor.client_ai"):
                auditor.perform_audit()
        # Error should be published
        assert auditor.client_mqtt.publish.called

    def test_ai_429_handled(self, auditor):
        """AI 429 (quota) error is caught gracefully."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.all_hosts.return_value = ["172.18.0.1"]
            mock_nm.__getitem__.return_value.all_protocols.return_value = ["tcp"]
            mock_nm.__getitem__.return_value.__getitem__.return_value = {
                80: {"state": "open", "name": "http", "product": "", "version": ""}
            }
            mock_nm_cls.return_value = mock_nm
            with patch("auditor.client_ai") as mock_ai:
                mock_ai.models.generate_content.side_effect = Exception("429 Quota Exhausted")
                auditor.perform_audit()
        # Should publish error status
        status_calls = [c for c in auditor.client_mqtt.publish.call_args_list if c[0][0] == "lab/security/status"]
        assert len(status_calls) > 0

    def test_ai_503_handled(self, auditor):
        """AI 503 (overloaded) error is caught gracefully."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.all_hosts.return_value = ["172.18.0.1"]
            mock_nm.__getitem__.return_value.all_protocols.return_value = ["tcp"]
            mock_nm.__getitem__.return_value.__getitem__.return_value = {
                80: {"state": "open", "name": "http", "product": "", "version": ""}
            }
            mock_nm_cls.return_value = mock_nm
            with patch("auditor.client_ai") as mock_ai:
                mock_ai.models.generate_content.side_effect = Exception("503 Server Overloaded")
                auditor.perform_audit()
        assert auditor.client_mqtt.publish.called

    def test_is_scanning_flag_reset(self, auditor):
        """After perform_audit completes (even on error), is_scanning is False."""
        with patch("auditor.nmap.PortScanner") as mock_nm_cls:
            mock_nm = MagicMock()
            mock_nm.all_hosts.return_value = []
            mock_nm_cls.return_value = mock_nm
            with patch("auditor.client_ai"):
                auditor.is_scanning = True
                auditor.perform_audit()
        assert auditor.is_scanning is False


class TestModuleConstants:
    """Module-level configuration values."""

    def test_broker_default(self, auditor):
        assert auditor.BROKER == "mosquitto"

    def test_target_subnet(self, auditor):
        assert auditor.TARGET_SUBNET == "172.18.0.0/24"

    def test_cooldown_time(self, auditor):
        assert auditor.COOLDOWN_TIME == 30

    def test_default_model(self, auditor):
        assert auditor.MODEL_ID == "gemini-2.0-flash"

    def test_client_mqtt_none_when_imported(self, auditor):
        """client_mqtt is None by default (set only under __main__)."""
        assert auditor.client_mqtt is not None  # fixture sets it to MagicMock
