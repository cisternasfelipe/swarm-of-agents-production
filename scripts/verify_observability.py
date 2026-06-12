#!/usr/bin/env python3
import sys
import sqlite3
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from observability.store import EventStore

DB_PATH = Path("/tmp/test_observability.db")


def test_event_store():
    DB_PATH.unlink(missing_ok=True)

    store = EventStore(DB_PATH)
    run_id = str(uuid.uuid4())

    store.create_run(run_id, "delegate", "Test task", "/tmp")
    store.emit(run_id, "run_started", summary="Test task")
    store.emit(run_id, "agent_started", agent="frontend_dev")
    store.emit(run_id, "agent_finished", agent="frontend_dev", summary="Done")
    store.finish_run(run_id, "success")

    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT id, kind, status FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row is not None, "Run not found"
    assert row[1] == "delegate"
    assert row[2] == "success"
    print(f"OK: run created ({row[0][:8]}...)")

    events = conn.execute(
        "SELECT seq, type, agent FROM events WHERE run_id = ? ORDER BY seq", (run_id,)
    ).fetchall()
    assert len(events) == 3, f"Expected 3 events, got {len(events)}"
    assert events[0][1] == "run_started"
    assert events[1][1] == "agent_started"
    assert events[2][1] == "agent_finished"
    for seq, etype, agent in events:
        print(f"  seq={seq} type={etype} agent={agent}")

    conn.close()
    print("OK: all assertions passed")


def test_fail_open():
    store = EventStore("/nonexistent/path/to/observability.db")
    store.create_run("x", "delegate", "t", "/tmp")
    store.emit("x", "run_started")
    store.finish_run("x", "success")
    print("OK: fail-open works (no exception raised)")


def test_summary_truncation():
    DB_PATH.unlink(missing_ok=True)
    store = EventStore(DB_PATH)
    run_id = str(uuid.uuid4())
    store.create_run(run_id, "delegate", "t", "/tmp")
    long_text = "x" * 1000
    store.emit(run_id, "agent_finished", agent="test", summary=long_text)
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT summary FROM events WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert len(row[0]) <= 500, f"Summary not truncated: {len(row[0])} chars"
    conn.close()
    print("OK: summary truncated to 500 chars")


if __name__ == "__main__":
    test_event_store()
    test_fail_open()
    test_summary_truncation()
    print("\nAll tests passed.")
