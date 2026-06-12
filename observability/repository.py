import sqlite3
import json
from pathlib import Path
from typing import Optional

from config import OBSERVABILITY_DB_PATH


class ReadRepository:
    def __init__(self, db_path: Optional[str | Path] = None):
        self._db_path = str(db_path or OBSERVABILITY_DB_PATH)

    def _connect(self, mode: str = "ro") -> sqlite3.Connection:
        if mode == "ro":
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        else:
            conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _dict_row(self, row: sqlite3.Row) -> dict:
        if row is None:
            return None
        return dict(row)

    def _dict_rows(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in (rows or [])]

    def get_health(self) -> dict:
        conn = self._connect()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total_runs,
                    COALESCE(SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END), 0) AS running,
                    COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) AS success,
                    COALESCE(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END), 0) AS failed
                FROM runs
            """).fetchone()
            result = self._dict_row(row)
            total = result["total_runs"]
            result["db_ok"] = True
            result["success_rate"] = (
                round(result["success"] / total * 100, 1) if total > 0 else None
            )
            return result
        finally:
            conn.close()

    def run_exists(self, run_id: str) -> bool:
        conn = self._connect()
        try:
            row = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_run(self, run_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, kind, task, project_path, status, started_at, finished_at "
                "FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            result = self._dict_row(row)
            result["duration_ms"] = self._compute_duration(result)
            result["n_iterations"] = self._count_iterations(conn, run_id)
            result["agents"] = self._list_agents(conn, run_id)
            return result
        finally:
            conn.close()

    def list_runs(
        self, limit: int = 20, status: Optional[str] = None, before: Optional[str] = None
    ) -> list[dict]:
        conn = self._connect()
        try:
            query = """
                SELECT id, kind, task, project_path, status, started_at, finished_at
                FROM runs
                WHERE 1=1
            """
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if before:
                query += " AND started_at < ?"
                params.append(before)
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                r = self._dict_row(row)
                r["duration_ms"] = self._compute_duration(r)
                r["n_iterations"] = self._count_iterations(conn, r["id"])
                r["agents"] = self._list_agents(conn, r["id"])
                results.append(r)
            return results
        finally:
            conn.close()

    def get_events(
        self, run_id: str, after_seq: int = 0, limit: int = 100
    ) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT seq, ts, type, agent, iteration, summary, payload "
                "FROM events WHERE run_id = ? AND seq > ? "
                "ORDER BY seq LIMIT ?",
                (run_id, after_seq, limit),
            ).fetchall()
            return [self._parse_event_row(r) for r in rows]
        finally:
            conn.close()

    def get_loop_events(self, run_id: str) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT seq, type, iteration, payload "
                "FROM events WHERE run_id = ? "
                "AND type IN ('loop_iteration_started', 'qa_verdict', 'review_verdict', 'fix_requested') "
                "ORDER BY seq",
                (run_id,),
            ).fetchall()
            return self._dict_rows(rows)
        finally:
            conn.close()

    def get_max_event_seq(self, run_id: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return row[0]
        finally:
            conn.close()

    def get_plan(self, run_id: str) -> Optional[dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT payload FROM events WHERE run_id = ? AND type = 'plan_created' "
                "ORDER BY seq LIMIT 1",
                (run_id,),
            ).fetchone()
            if not row or not row["payload"]:
                return None
            return json.loads(row["payload"])
        except (json.JSONDecodeError, TypeError):
            return None
        finally:
            conn.close()

    def _compute_duration(self, run: dict) -> Optional[int]:
        if not run.get("started_at") or not run.get("finished_at"):
            return None
        try:
            started = run["started_at"]
            finished = run["finished_at"]
            st = self._parse_iso(started)
            ft = self._parse_iso(finished)
            return int((ft - st).total_seconds() * 1000)
        except (ValueError, TypeError):
            return None

    def _count_iterations(self, conn: sqlite3.Connection, run_id: str) -> int:
        row = conn.execute(
            "SELECT COUNT(DISTINCT iteration) FROM events "
            "WHERE run_id = ? AND iteration IS NOT NULL",
            (run_id,),
        ).fetchone()
        return row[0]

    def _list_agents(self, conn: sqlite3.Connection, run_id: str) -> list[str]:
        rows = conn.execute(
            "SELECT DISTINCT agent FROM events "
            "WHERE run_id = ? AND agent IS NOT NULL "
            "ORDER BY agent",
            (run_id,),
        ).fetchall()
        return [r[0] for r in rows]

    def _parse_event_row(self, row: sqlite3.Row) -> dict:
        result = {
            "seq": row["seq"],
            "ts": row["ts"],
            "type": row["type"],
            "agent": row["agent"],
            "iteration": row["iteration"],
            "summary": row["summary"],
            "payload": None,
        }
        if row["payload"]:
            try:
                result["payload"] = json.loads(row["payload"])
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def _parse_iso(self, ts: str):
        from datetime import datetime
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
