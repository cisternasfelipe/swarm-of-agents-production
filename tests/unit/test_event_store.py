import sqlite3
import uuid
import pytest
from pathlib import Path

from observability.store import EventStore


class TestEventStoreCRUD:
    def test_create_run(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "team", "Test task", "/tmp")
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("SELECT id, kind, task, status FROM runs WHERE id=?", (run_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "team"
        assert row[3] == "running"

    def test_finish_run(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.finish_run(run_id, "success")
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("SELECT status, finished_at FROM runs WHERE id=?", (run_id,)).fetchone()
        conn.close()
        assert row[0] == "success"
        assert row[1] is not None

    def test_emit_sequence_monotonic(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.emit(run_id, "run_started")
        store.emit(run_id, "agent_started", agent="test")
        store.emit(run_id, "agent_finished", agent="test", summary="Done")
        conn = sqlite3.connect(tmp_db_path)
        rows = conn.execute(
            "SELECT seq, type FROM events WHERE run_id=? ORDER BY seq", (run_id,)
        ).fetchall()
        conn.close()
        assert [r[0] for r in rows] == [1, 2, 3]
        assert [r[1] for r in rows] == ["run_started", "agent_started", "agent_finished"]

    def test_emit_summary_truncated(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.emit(run_id, "agent_finished", agent="test", summary="x" * 1000)
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("SELECT summary FROM events WHERE run_id=?", (run_id,)).fetchone()
        conn.close()
        assert len(row[0]) <= 500

    def test_emit_payload_stored_as_json(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.emit(run_id, "guardrail_triggered", payload={"tool": "write_file", "result": "block"})
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("SELECT payload FROM events WHERE run_id=?", (run_id,)).fetchone()
        conn.close()
        assert '"tool"' in row[0]
        assert '"block"' in row[0]

    def test_emit_iteration_field(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "team", "T", "/tmp")
        store.emit(run_id, "loop_iteration_started", iteration=2)
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("SELECT iteration FROM events WHERE run_id=?", (run_id,)).fetchone()
        conn.close()
        assert row[0] == 2


class TestEventStoreFailOpen:
    def test_fail_open_init(self, tmp_path):
        bad_path = tmp_path / "sub" / "sub2" / "observability.db"
        store = EventStore(str(bad_path))
        run_id = "x"
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.emit(run_id, "run_started")
        store.finish_run(run_id, "success")

    def test_fail_open_disabled(self, monkeypatch):
        monkeypatch.setattr("config.OBSERVABILITY_ENABLED", False)
        store = EventStore("/tmp/nonexistent/test.db")
        store.create_run("x", "delegate", "T", "/tmp")
        store.emit("x", "run_started")
        store.finish_run("x", "success")

    def test_fail_open_invalid_kind(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        store.create_run(str(uuid.uuid4()), "invalid_kind", "T", "/tmp")

    def test_fail_open_duplicate_run_id(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "T", "/tmp")
        store.create_run(run_id, "delegate", "T2", "/tmp")


class TestEventStoreWAL:
    def test_wal_mode_enabled(self, tmp_db_path):
        store = EventStore(tmp_db_path)
        store.create_run(str(uuid.uuid4()), "delegate", "T", "/tmp")
        conn = sqlite3.connect(tmp_db_path)
        row = conn.execute("PRAGMA journal_mode").fetchone()
        conn.close()
        assert row[0].lower() == "wal"
