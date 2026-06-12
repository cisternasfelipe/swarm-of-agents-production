from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    id: str
    kind: str
    task: str = Field(description="First 200 chars of task description")
    project_path: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = Field(None, description="Computed. Null if still running.")
    n_iterations: int = 0
    agents: list[str] = Field(default_factory=list)


class LoopIteration(BaseModel):
    iteration: int
    qa_verdict: Optional[str] = None
    review_verdict: Optional[str] = None
    fix_count: int = 0


class RunDetail(RunSummary):
    loop_summary: list[LoopIteration] = Field(default_factory=list)
    plan: Optional[dict] = None


class EventItem(BaseModel):
    seq: int
    ts: str
    type: str
    agent: Optional[str] = None
    iteration: Optional[int] = None
    summary: Optional[str] = None
    payload: Optional[dict] = None


class HealthResponse(BaseModel):
    db_ok: bool
    total_runs: int = 0
    running: int = 0
    success: int = 0
    failed: int = 0
    success_rate: Optional[float] = None


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
