import uuid
import json
import pytest
from fastapi.testclient import TestClient

from observability.api import app
from observability.repository import ReadRepository
from observability.store import EventStore


@pytest.fixture
def tmp_event_store(tmp_path):
    db_path = str(tmp_path / "test_api.db")
    store = EventStore(db_path)
    yield store, db_path


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_api.db")
    monkeypatch.setattr("config.OBSERVABILITY_DB_PATH", db_path)
    store = EventStore(db_path)
    from observability.api import _repo as api_repo
    monkeypatch.setattr(api_repo, "_db_path", db_path)
    client = TestClient(app)
    run_id = str(uuid.uuid4())
    store.create_run(run_id, "delegate", "Test task for API", "/tmp/test")
    store.emit(run_id, "run_started", summary="Test task for API")
    store.emit(run_id, "agent_started", agent="frontend_dev")
    store.emit(run_id, "agent_finished", agent="frontend_dev",
               summary="All good")
    store.finish_run(run_id, "success")
    yield client, run_id, store, db_path


class TestHealthEndpoint:
    def test_health_returns_200(self, api_client):
        client, _, _, _ = api_client
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["db_ok"] is True
        assert "total_runs" in body
        assert "running" in body
        assert "success" in body

    def test_health_zero_runs(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        store = EventStore(db_path)
        repo = ReadRepository(db_path)
        health = repo.get_health()
        assert health["total_runs"] == 0
        assert health["success_rate"] is None


class TestListRuns:
    def test_list_runs(self, api_client):
        client, run_id, _, _ = api_client
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        assert body[0]["kind"] == "delegate"
        assert "duration_ms" in body[0]
        assert "agents" in body[0]

    def test_list_runs_filter_status(self, api_client):
        client, _, store, db_path = api_client
        run2 = str(uuid.uuid4())
        store.create_run(run2, "team", "Failed task", "/tmp")
        store.finish_run(run2, "error")
        repo = ReadRepository(db_path)
        from observability.api import _repo as api_repo
        api_repo._db_path = db_path
        resp = client.get("/api/runs?status=error")
        assert resp.status_code == 200

    def test_list_runs_limit(self, api_client):
        client, _, store, db_path = api_client
        for i in range(5):
            rid = str(uuid.uuid4())
            store.create_run(rid, "delegate", f"t{i}", "/tmp")
            store.finish_run(rid, "success")
        repo = ReadRepository(db_path)
        from observability.api import _repo as api_repo
        api_repo._db_path = db_path
        resp = client.get("/api/runs?limit=3")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_list_runs_invalid_status(self, api_client):
        client, _, _, _ = api_client
        resp = client.get("/api/runs?status=unknown")
        assert resp.status_code == 422


class TestGetRun:
    def test_get_run(self, api_client):
        client, run_id, _, _ = api_client
        resp = client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == run_id
        assert body["kind"] == "delegate"
        assert "loop_summary" in body
        assert "plan" in body

    def test_get_run_not_found(self, api_client):
        client, _, _, _ = api_client
        resp = client.get("/api/runs/nonexistent-run-id")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body


class TestGetEvents:
    def test_get_events(self, api_client):
        client, run_id, _, _ = api_client
        resp = client.get(f"/api/runs/{run_id}/events")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 3
        assert body[0]["type"] == "run_started"

    def test_get_events_after_seq(self, api_client):
        client, run_id, _, _ = api_client
        resp = client.get(f"/api/runs/{run_id}/events?after_seq=1")
        assert resp.status_code == 200
        body = resp.json()
        for e in body:
            assert e["seq"] > 1

    def test_get_events_not_found(self, api_client):
        client, _, _, _ = api_client
        resp = client.get("/api/runs/nonexistent/events")
        assert resp.status_code == 404


class TestLoopSummary:
    def test_build_loop_summary(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "loop_test.db")
        store = EventStore(db_path)
        run_id = str(uuid.uuid4())
        store.create_run(run_id, "team", "Loop test", "/tmp")
        store.emit(run_id, "run_started")
        store.emit(run_id, "loop_iteration_started", iteration=1)
        store.emit(run_id, "qa_verdict", agent="qa_tester", iteration=1,
                   payload={"verdict": "FAIL"})
        store.emit(run_id, "fix_requested", agent="backend_dev", iteration=1)
        store.emit(run_id, "loop_iteration_started", iteration=2)
        store.emit(run_id, "qa_verdict", agent="qa_tester", iteration=2,
                   payload={"verdict": "PASS"})
        store.emit(run_id, "review_verdict", agent="code_reviewer", iteration=2,
                   payload={"verdict": "APPROVE"})
        store.finish_run(run_id, "success")

        repo = ReadRepository(db_path)
        monkeypatch.setattr("observability.api._repo", repo)
        from observability.api import _build_loop_summary
        loops = _build_loop_summary(run_id)
        assert len(loops) == 2
        assert loops[0]["iteration"] == 1
        assert loops[0]["qa_verdict"] == "FAIL"
        assert loops[0]["fix_count"] == 1
        assert loops[1]["iteration"] == 2
        assert loops[1]["qa_verdict"] == "PASS"
        assert loops[1]["review_verdict"] == "APPROVE"
