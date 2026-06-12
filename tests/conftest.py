import sys
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_db_path(tmp_path):
    db = tmp_path / "test_observability.db"
    yield str(db)
    for suffix in ["", "-wal", "-shm"]:
        p = tmp_path / f"test_observability.db{suffix}"
        p.unlink(missing_ok=True)


@pytest.fixture
def tmp_metrics_path(tmp_path, monkeypatch):
    metrics_file = tmp_path / "metrics.json"
    monkeypatch.setattr("utils.metrics.BASE_DIR", tmp_path)
    yield metrics_file
    metrics_file.unlink(missing_ok=True)


@pytest.fixture
def tmp_chroma_path(tmp_path, monkeypatch):
    chroma_dir = tmp_path / "chroma_db"
    monkeypatch.setattr("config.CHROMA_DB_PATH", chroma_dir)
    yield chroma_dir


@pytest.fixture
def mock_event_store():
    store = MagicMock()
    store.create_run = MagicMock()
    store.finish_run = MagicMock()
    store.emit = MagicMock()
    return store


@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.store_decision = MagicMock()
    r.store_bug = MagicMock()
    r.store_pattern = MagicMock()
    r.get_context = MagicMock(return_value="")
    r.retrieve = MagicMock(return_value=[])
    return r


@pytest.fixture
def mock_knowledge_base():
    kb = MagicMock()
    kb.get_collection = MagicMock()
    kb.store = MagicMock()
    kb.query = MagicMock(return_value=[])
    kb.list_projects = MagicMock(return_value=[])
    return kb


@pytest.fixture
def mock_embedder():
    e = MagicMock()
    e.embed = MagicMock(return_value=[0.1, 0.2, 0.3])
    e.embed_batch = MagicMock(return_value=[[0.1, 0.2, 0.3]])
    return e


@pytest.fixture
def mock_agent_stream_allowed():
    """Simulates agent stream that makes 1 tool call and returns text."""
    async def _stream(instructions=""):
        from agentscope.event import (
            TextBlockDeltaEvent,
            RequireUserConfirmEvent,
        )
        from agentscope.message._block import ToolCallBlock
        yield TextBlockDeltaEvent(
            reply_id="r1", block_id="b1", delta="Thinking..."
        )
        yield RequireUserConfirmEvent(
            reply_id="r1",
            tool_calls=[
                ToolCallBlock(
                    id="call_1",
                    name="mcp__filesystem__write_file",
                    input='{"path": "/tmp/test.jsx", "content": "test"}',
                )
            ],
        )
        yield TextBlockDeltaEvent(
            reply_id="r1", block_id="b1", delta="Done."
        )
    return _stream


@pytest.fixture
def mock_agent_stream_blocked():
    """Simulates agent stream making a blocked tool call."""
    async def _stream(instructions=""):
        from agentscope.event import (
            TextBlockDeltaEvent,
            RequireUserConfirmEvent,
        )
        from agentscope.message._block import ToolCallBlock
        yield TextBlockDeltaEvent(
            reply_id="r1", block_id="b1", delta="Trying to write..."
        )
        yield RequireUserConfirmEvent(
            reply_id="r1",
            tool_calls=[
                ToolCallBlock(
                    id="call_1",
                    name="mcp__filesystem__write_file",
                    input='{"path": "/tmp/src/api/users.py", "content": "malicious"}',
                )
            ],
        )
        yield TextBlockDeltaEvent(
            reply_id="r1", block_id="b1", delta="Blocked."
        )
    return _stream


@pytest.fixture
def clean_singletons():
    from rag.embedder import Embedder
    Embedder._instance = None
    try:
        Embedder._model = None
    except AttributeError:
        pass
    yield
    Embedder._instance = None
    try:
        Embedder._model = None
    except AttributeError:
        pass


@pytest.fixture
def mock_create_agent():
    """Returns a factory that creates mocked agents for orchestrator tests."""
    def _factory(agent_results=None):
        if agent_results is None:
            agent_results = {}
        def create(role, project_path, read_only=False, run_id=None, event_store=None):
            agent = MagicMock()
            agent.role = role
            agent.run = AsyncMock(return_value=agent_results.get(
                role, f"Mock result from {role}"
            ))
            return agent
        return create
    return _factory
