import json
import time
from pathlib import Path
from typing import Optional

from config import BASE_DIR


class Metrics:
    def __init__(self):
        self._file = BASE_DIR / "data" / "metrics.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self._file.exists():
            return json.loads(self._file.read_text())
        return {
            "agents": {},
            "tasks": {"total": 0, "success": 0, "failed": 0},
            "guardrails": {"blocked": 0, "warned": 0, "by_role": {}},
        }

    def _save(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._data, indent=2))

    def record_agent_call(self, agent: str, tokens: int = 0, duration_ms: int = 0):
        if agent not in self._data["agents"]:
            self._data["agents"][agent] = {"calls": 0, "tokens": 0, "total_ms": 0}
        self._data["agents"][agent]["calls"] += 1
        self._data["agents"][agent]["tokens"] += tokens
        self._data["agents"][agent]["total_ms"] += duration_ms
        self._save()

    def record_task(self, success: bool):
        self._data["tasks"]["total"] += 1
        if success:
            self._data["tasks"]["success"] += 1
        else:
            self._data["tasks"]["failed"] += 1
        self._save()

    def record_guardrail_violation(self, role: str, violation_type: str):
        if "guardrails" not in self._data:
            self._data["guardrails"] = {"blocked": 0, "warned": 0, "by_role": {}}

        if violation_type == "block":
            self._data["guardrails"]["blocked"] += 1
        elif violation_type == "warn":
            self._data["guardrails"]["warned"] += 1

        if role not in self._data["guardrails"]["by_role"]:
            self._data["guardrails"]["by_role"][role] = {"blocked": 0, "warned": 0}

        if violation_type == "block":
            self._data["guardrails"]["by_role"][role]["blocked"] += 1
        elif violation_type == "warn":
            self._data["guardrails"]["by_role"][role]["warned"] += 1

        self._save()

    def get_summary(self) -> dict:
        return self._data
