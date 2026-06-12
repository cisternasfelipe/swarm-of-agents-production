import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

from config import OBSERVABILITY_ENABLED
from utils.logger import get_logger

logger = get_logger("event_store")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('team', 'delegate')),
    task TEXT NOT NULL,
    project_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK(status IN ('running', 'success', 'error')),
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(id),
    seq INTEGER NOT NULL,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    agent TEXT,
    iteration INTEGER,
    summary TEXT CHECK(length(summary) <= 500),
    payload TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
"""


class EventStore:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        self._seq_lock = Lock()
        self._ready = False
        if OBSERVABILITY_ENABLED:
            self._init_db()

    def _init_db(self):
        try:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            conn.close()
            self._ready = True
        except Exception as e:
            logger.error("event_store_init_failed", error=str(e))

    def _enabled(self) -> bool:
        return OBSERVABILITY_ENABLED and self._ready and bool(self._db_path)

    def create_run(self, run_id: str, kind: str, task: str, project_path: str):
        if not self._enabled():
            return
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute(
                "INSERT INTO runs (id, kind, task, project_path, status, started_at) "
                "VALUES (?, ?, ?, ?, 'running', ?)",
                (run_id, kind, task, project_path, self._now()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("event_store_create_run_failed", error=str(e))

    def finish_run(self, run_id: str, status: str):
        if not self._enabled():
            return
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                (status, self._now(), run_id),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("event_store_finish_run_failed", error=str(e))

    def emit(
        self,
        run_id: str,
        event_type: str,
        agent: str | None = None,
        iteration: int | None = None,
        summary: str | None = None,
        payload: dict | None = None,
    ):
        if not self._enabled():
            return
        try:
            seq = self._next_seq(run_id)
            payload_str = json.dumps(payload) if payload else None
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute(
                "INSERT INTO events (run_id, seq, ts, type, agent, iteration, summary, payload) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    seq,
                    self._now(),
                    event_type,
                    agent,
                    iteration,
                    (summary or "")[:500],
                    payload_str,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("event_store_emit_failed", error=str(e), event_type=event_type)

    def _next_seq(self, run_id: str) -> int:
        with self._seq_lock:
            conn = sqlite3.connect(self._db_path, timeout=5)
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            conn.close()
            return row[0]

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
