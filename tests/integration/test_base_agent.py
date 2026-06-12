import json
import pytest
from unittest.mock import MagicMock, AsyncMock, PropertyMock, patch

from agents.base_agent import BaseAgent


class TestStoreKnowledge:
    @pytest.fixture
    def agent(self, mock_retriever):
        with patch.object(BaseAgent, "__init__", lambda self, **kw: None):
            a = BaseAgent.__new__(BaseAgent)
            a.role = "test"
            a.project_path = "/tmp"
            a._retriever = mock_retriever
            return a

    def test_bug_detected(self, agent):
        agent._store_knowledge("fix the bug in login", "Fixed")
        agent._retriever.store_bug.assert_called_once()
        agent._retriever.store_pattern.assert_not_called()
        agent._retriever.store_decision.assert_not_called()

    def test_fix_detected(self, agent):
        agent._store_knowledge("fix the api endpoint", "Fixed")
        agent._retriever.store_bug.assert_called_once()

    def test_architecture_detected(self, agent):
        agent._store_knowledge("design architecture for microservices", "Done")
        agent._retriever.store_pattern.assert_called_once()
        agent._retriever.store_bug.assert_not_called()
        agent._retriever.store_decision.assert_not_called()

    def test_default_decision(self, agent):
        agent._store_knowledge("create homepage", "Created")
        agent._retriever.store_decision.assert_called_once()
        agent._retriever.store_bug.assert_not_called()
        agent._retriever.store_pattern.assert_not_called()

    def test_swallows_exceptions(self, agent):
        agent._retriever.store_decision.side_effect = RuntimeError("DB down")
        agent._store_knowledge("create homepage", "Created")

    def test_bug_takes_precedence_over_architecture(self, agent):
        agent._store_knowledge("fix bug in architecture", "Fixed")
        agent._retriever.store_bug.assert_called_once()
        agent._retriever.store_pattern.assert_not_called()


class TestRunEmitsEvents:
    @pytest.fixture
    def agent(self, mock_event_store, mock_retriever):
        with patch.object(BaseAgent, "__init__", lambda self, **kw: None):
            a = BaseAgent.__new__(BaseAgent)
            a.role = "frontend_dev"
            a.project_path = "/tmp"
            a._run_id = "test-run-123"
            a._event_store = mock_event_store
            a._retriever = mock_retriever
            a._rate_limiter = MagicMock()
            a._logger = MagicMock()
            a._metrics = MagicMock()
            a._agent = MagicMock()

            async def mock_stream(inputs):
                from agentscope.event import TextBlockDeltaEvent
                yield TextBlockDeltaEvent(reply_id="r1", block_id="b1", delta="Hello ")
                yield TextBlockDeltaEvent(reply_id="r1", block_id="b1", delta="World")
            a._agent.reply_stream = mock_stream

            a._cleanup = AsyncMock()
            a._ensure_agent = AsyncMock()
            return a

    @pytest.mark.asyncio
    async def test_emits_agent_started(self, agent, mock_event_store):
        await agent.run("create test file")
        mock_event_store.emit.assert_any_call("test-run-123", "agent_started", agent="frontend_dev")

    @pytest.mark.asyncio
    async def test_emits_agent_finished(self, agent, mock_event_store):
        await agent.run("create test file")
        mock_event_store.emit.assert_any_call("test-run-123", "agent_finished",
                                              agent="frontend_dev", summary="Hello World")

    @pytest.mark.asyncio
    async def test_no_event_store_no_crash(self, agent):
        agent._event_store = None
        agent._run_id = None
        result = await agent.run("test")
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_cleanup_always_called(self, agent):
        await agent.run("test")
        agent._cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_failed_emitted_on_exception(self, agent, mock_event_store):
        agent._ensure_agent.side_effect = RuntimeError("MCP connection failed")
        with pytest.raises(RuntimeError):
            await agent.run("test")
        mock_event_store.emit.assert_any_call("test-run-123", "agent_failed",
                                              agent="frontend_dev",
                                              summary="MCP connection failed")

    @pytest.mark.asyncio
    async def test_cleanup_called_after_exception(self, agent):
        agent._ensure_agent.side_effect = RuntimeError("fail")
        with pytest.raises(RuntimeError):
            await agent.run("test")
        agent._cleanup.assert_called_once()


class TestGuardrailEmits:
    @pytest.fixture
    def agent(self, mock_event_store, mock_retriever):
        with patch.object(BaseAgent, "__init__", lambda self, **kw: None):
            a = BaseAgent.__new__(BaseAgent)
            a.role = "frontend_dev"
            a.project_path = "/tmp"
            a._run_id = "test-run-456"
            a._event_store = mock_event_store
            a._retriever = mock_retriever
            a._rate_limiter = MagicMock()
            a._logger = MagicMock()
            a._metrics = MagicMock()
            a._agent = MagicMock()

            call_count = [0]
            async def mock_blocked_stream(inputs):
                from agentscope.event import TextBlockDeltaEvent, RequireUserConfirmEvent
                from agentscope.message._block import ToolCallBlock
                call_count[0] += 1
                if call_count[0] == 1:
                    yield TextBlockDeltaEvent(reply_id="r1", block_id="b1", delta="Trying")
                    yield RequireUserConfirmEvent(
                        reply_id="r1",
                        tool_calls=[
                            ToolCallBlock(
                                id="call_1",
                                name="mcp__filesystem__write_file",
                                input='{"path": "/tmp/src/api/users.py", "content": "x"}',
                            )
                        ],
                    )
                yield TextBlockDeltaEvent(reply_id="r1", block_id="b1", delta="Done")
            a._agent.reply_stream = mock_blocked_stream

            a._cleanup = AsyncMock()
            a._ensure_agent = AsyncMock()
            return a

    @pytest.mark.asyncio
    async def test_emits_guardrail_triggered(self, agent, mock_event_store):
        await agent.run("write to api folder")
        emit_calls = mock_event_store.emit.call_args_list
        guardrail_found = False
        for c in emit_calls:
            args, kwargs = c[0], c[1] if len(c) > 1 else {}
            if len(args) >= 2 and args[1] == "guardrail_triggered":
                guardrail_found = True
                if "payload" in kwargs:
                    assert kwargs["payload"]["result"] == "block"
        assert guardrail_found, f"No guardrail_triggered event found in {emit_calls}"
