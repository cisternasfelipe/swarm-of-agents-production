import json
import pytest
from pathlib import Path

from utils.metrics import Metrics


class TestMetrics:
    @pytest.fixture
    def metrics(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.metrics.BASE_DIR", tmp_path)
        return Metrics()

    def test_record_agent_call_initializes(self, metrics):
        metrics.record_agent_call("frontend_dev")
        summary = metrics.get_summary()
        assert "frontend_dev" in summary["agents"]
        assert summary["agents"]["frontend_dev"]["calls"] == 1

    def test_record_agent_call_increments(self, metrics):
        metrics.record_agent_call("frontend_dev")
        metrics.record_agent_call("frontend_dev")
        assert metrics.get_summary()["agents"]["frontend_dev"]["calls"] == 2

    def test_record_task_success(self, metrics):
        metrics.record_task(True)
        s = metrics.get_summary()["tasks"]
        assert s["total"] == 1
        assert s["success"] == 1
        assert s["failed"] == 0

    def test_record_task_failure(self, metrics):
        metrics.record_task(False)
        s = metrics.get_summary()["tasks"]
        assert s["total"] == 1
        assert s["failed"] == 1

    def test_record_guardrail_block(self, metrics):
        metrics.record_guardrail_violation("frontend_dev", "block")
        g = metrics.get_summary()["guardrails"]
        assert g["blocked"] == 1
        assert g["by_role"]["frontend_dev"]["blocked"] == 1

    def test_record_guardrail_warn(self, metrics):
        metrics.record_guardrail_violation("backend_dev", "warn")
        g = metrics.get_summary()["guardrails"]
        assert g["warned"] == 1
        assert g["by_role"]["backend_dev"]["warned"] == 1

    def test_record_guardrail_unknown_type(self, metrics):
        metrics.record_guardrail_violation("frontend_dev", "unknown")
        g = metrics.get_summary()["guardrails"]
        assert g["blocked"] == 0
        assert g["warned"] == 0

    def test_persistence(self, tmp_path, monkeypatch):
        monkeypatch.setattr("utils.metrics.BASE_DIR", tmp_path)
        m1 = Metrics()
        m1.record_agent_call("test")
        m2 = Metrics()
        assert m2.get_summary()["agents"]["test"]["calls"] == 1

    def test_get_summary_is_live_reference(self, metrics):
        metrics.record_agent_call("test")
        s1 = metrics.get_summary()
        metrics.record_agent_call("test")
        s2 = metrics.get_summary()
        assert s1 is s2
        assert s1["agents"]["test"]["calls"] == 2

    def test_multiple_roles_guardrail(self, metrics):
        metrics.record_guardrail_violation("frontend_dev", "block")
        metrics.record_guardrail_violation("backend_dev", "warn")
        by_role = metrics.get_summary()["guardrails"]["by_role"]
        assert by_role["frontend_dev"]["blocked"] == 1
        assert by_role["backend_dev"]["warned"] == 1
