import uuid
import sqlite3
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from observability.store import EventStore


class TestObservabilityE2E:
    @pytest.fixture
    def tmp_obs_db(self, tmp_path):
        db_path = str(tmp_path / "obs_e2e.db")
        store = EventStore(db_path)
        yield store, db_path

    @pytest.mark.asyncio
    async def test_full_delegate_sequence(self, tmp_obs_db):
        store, db_path = tmp_obs_db
        mock_agent = MagicMock()
        mock_agent.role = "frontend_dev"
        mock_agent.run = AsyncMock(return_value="Task completed")

        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "test task", "/tmp")
        store.emit(run_id, "run_started", summary="test task")
        store.emit(run_id, "agent_started", agent="frontend_dev")
        store.emit(run_id, "agent_finished", agent="frontend_dev", summary="Task completed")
        store.finish_run(run_id, "success")

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT seq, type, agent FROM events ORDER BY seq").fetchall()
        conn.close()
        event_types = [r[1] for r in rows]
        assert "run_started" in event_types
        assert "agent_started" in event_types
        assert "agent_finished" in event_types
        assert "run_finished" not in event_types  # it's an event, finish_run is a separate operation

    @pytest.mark.asyncio
    async def test_error_run_captured(self, tmp_obs_db):
        store, db_path = tmp_obs_db
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "test", "/tmp")
        store.emit(run_id, "run_started")
        store.emit(run_id, "agent_failed", agent="frontend_dev", summary="Error: crash")
        store.finish_run(run_id, "error")

        conn = sqlite3.connect(db_path)
        run = conn.execute("SELECT id, status FROM runs WHERE id=?", (run_id,)).fetchone()
        conn.close()
        assert run[1] == "error"

    def test_run_never_left_dangling(self, tmp_obs_db):
        store, db_path = tmp_obs_db
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "delegate", "test", "/tmp")
        store.finish_run(run_id, "success")

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT id, status FROM runs").fetchall()
        conn.close()
        for row in rows:
            assert row[1] in ("success", "error")

    @pytest.mark.asyncio
    async def test_team_task_event_types(self, tmp_obs_db):
        store, db_path = tmp_obs_db
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "team", "build feature", "/tmp")
        store.emit(run_id, "run_started", summary="build feature")
        store.emit(run_id, "plan_created", agent="architect")
        store.emit(run_id, "agent_started", agent="frontend_dev")
        store.emit(run_id, "agent_finished", agent="frontend_dev", summary="Done")
        store.finish_run(run_id, "success")

        conn = sqlite3.connect(db_path)
        events = conn.execute("SELECT type FROM events ORDER BY seq").fetchall()
        conn.close()
        event_types = [e[0] for e in events]
        assert "run_started" in event_types
        assert "plan_created" in event_types
        assert "agent_started" in event_types
        assert "agent_finished" in event_types
