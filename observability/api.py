import asyncio
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import OBSERVABILITY_CORS_ORIGIN
from observability.repository import ReadRepository
from observability.models import (
    RunSummary,
    RunDetail,
    EventItem,
    HealthResponse,
    ProblemDetail,
    LoopIteration,
)

app = FastAPI(title="AgentScope Swarm — Observability API", version="0.1.0")
_repo = ReadRepository()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[OBSERVABILITY_CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found(run_id: str):
    raise HTTPException(
        status_code=404,
        detail=ProblemDetail(
            title="Run not found",
            status=404,
            detail=f"No run with id '{run_id}'",
            instance=f"/api/runs/{run_id}",
        ).model_dump(),
    )


def _build_loop_summary(run_id: str, repo=None) -> list[dict]:
    r = repo or _repo
    events = r.get_loop_events(run_id)
    loops: dict[int, dict] = {}
    for e in events:
        iteration = e.get("iteration")
        if iteration is None:
            continue
        if iteration not in loops:
            loops[iteration] = {"iteration": iteration, "qa_verdict": None,
                                 "review_verdict": None, "fix_count": 0}
        if e["type"] == "qa_verdict":
            payload = e.get("payload") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    pass
            loops[iteration]["qa_verdict"] = payload.get("verdict")
        elif e["type"] == "review_verdict":
            payload = e.get("payload") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    pass
            loops[iteration]["review_verdict"] = payload.get("verdict")
        elif e["type"] == "fix_requested":
            loops[iteration]["fix_count"] += 1
    return sorted(loops.values(), key=lambda x: x["iteration"])


@app.get("/api/health", response_model=HealthResponse)
def health():
    return _repo.get_health()


@app.get("/api/runs", response_model=list[RunSummary])
def list_runs(
    limit: int = Query(20, ge=1, le=200),
    status: Optional[str] = Query(None, pattern="^(running|success|error)$"),
    before: Optional[str] = Query(None, description="ISO timestamp cursor"),
):
    return _repo.list_runs(limit=limit, status=status, before=before)


@app.get("/api/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str):
    run = _repo.get_run(run_id)
    if not run:
        _not_found(run_id)
    run["loop_summary"] = _build_loop_summary(run_id)
    run["plan"] = _repo.get_plan(run_id)
    return run


@app.get("/api/runs/{run_id}/events", response_model=list[EventItem])
def get_events(
    run_id: str,
    after_seq: int = Query(0, ge=0, description="Return events with seq > this value"),
    limit: int = Query(100, ge=1, le=1000),
):
    if not _repo.run_exists(run_id):
        _not_found(run_id)
    return _repo.get_events(run_id, after_seq=after_seq, limit=limit)


@app.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str, after_seq: int = 0):
    await websocket.accept()

    if not _repo.run_exists(run_id):
        await websocket.send_json({"error": "run not found", "run_id": run_id})
        await websocket.close()
        return

    try:
        # Phase 1: replay existing events in batches
        while True:
            events = _repo.get_events(run_id, after_seq=after_seq, limit=100)
            if not events:
                break
            await websocket.send_json(events)
            after_seq = events[-1]["seq"]

        # Phase 2: live streaming
        run = _repo.get_run(run_id)
        no_change_count = 0
        while run and run["status"] == "running":
            events = _repo.get_events(run_id, after_seq=after_seq, limit=100)
            if events:
                await websocket.send_json(events)
                after_seq = events[-1]["seq"]
                no_change_count = 0
            else:
                no_change_count += 1
            await asyncio.sleep(0.5 if no_change_count < 10 else 1.0)
            run = _repo.get_run(run_id)

        # Phase 3: final events after finish
        final_events = _repo.get_events(run_id, after_seq=after_seq, limit=100)
        if final_events:
            await websocket.send_json(final_events)

        await websocket.send_json({"status": "run_finished", "run_id": run_id})
        await websocket.close()

    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
