import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

from orchestrator import Orchestrator
from config import MAX_LOOP_ITERATIONS


class TestParsePlan:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator.__new__(Orchestrator)

    def test_valid_json(self, orchestrator):
        plan = orchestrator._parse_plan('Result {"analysis": "ok", "subtasks": []} end')
        assert plan == {"analysis": "ok", "subtasks": []}

    def test_no_braces(self, orchestrator):
        assert orchestrator._parse_plan("no json here") is None

    def test_invalid_json(self, orchestrator):
        assert orchestrator._parse_plan("bad {invalid} here") is None

    def test_nested_json(self, orchestrator):
        plan = orchestrator._parse_plan('{"a": {"b": {"c": 1}}}')
        assert plan == {"a": {"b": {"c": 1}}}

    def test_markdown_code_fence(self, orchestrator):
        text = '```json\n{"analysis": "test", "subtasks": []}\n```'
        plan = orchestrator._parse_plan(text)
        assert plan == {"analysis": "test", "subtasks": []}

    def test_empty_string(self, orchestrator):
        assert orchestrator._parse_plan("") is None

    def test_only_opening_brace(self, orchestrator):
        assert orchestrator._parse_plan('{"a": 1') is None


class TestSummarizeAndCompile:
    @pytest.fixture
    def orchestrator(self):
        return Orchestrator.__new__(Orchestrator)

    def test_summarize_truncates(self, orchestrator):
        long_text = "x" * 600
        result = orchestrator._summarize_results({"dev": long_text})
        assert len(result.split("\n")[1]) <= 500

    def test_compile_all_sections(self, orchestrator):
        plan = {"analysis": "test analysis", "architecture_decisions": ["use sqlite"], "subtasks": []}
        output = orchestrator._compile_results("task", plan, {"dev": "result"})
        assert "task" in output
        assert "test analysis" in output
        assert "use sqlite" in output
        assert "dev" in output
        assert "result" in output

    def test_compile_missing_keys(self, orchestrator):
        plan = {}
        output = orchestrator._compile_results("task", plan, {})
        assert "N/A" in output


class TestOrchestratorFlow:
    @pytest.fixture
    def orchestrator(self, mock_event_store):
        with patch("orchestrator.EventStore", return_value=mock_event_store):
            o = Orchestrator("/tmp/test")
            return o

    @pytest.mark.asyncio
    async def test_delegate_task_success(self, orchestrator, mock_event_store):
        mock_agent = MagicMock()
        mock_agent.role = "frontend_dev"
        mock_agent.run = AsyncMock(return_value="Task done")
        with patch("orchestrator.create_agent", return_value=mock_agent):
            result = await orchestrator.delegate_task("test task", "frontend_dev")
        assert result.status == "success"
        assert "Task done" in result.output
        mock_event_store.create_run.assert_called_once()
        mock_event_store.finish_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegate_task_unknown_role(self, orchestrator):
        result = await orchestrator.delegate_task("test", "unknown_role")
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_delegate_task_agent_fails(self, orchestrator, mock_event_store):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("agent crash"))
        with patch("orchestrator.create_agent", return_value=mock_agent):
            result = await orchestrator.delegate_task("test", "frontend_dev")
        assert result.status == "error"
        mock_event_store.finish_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_team_task_no_subtasks(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        mock_architect.run = AsyncMock(return_value='Architect analysis')
        with patch("orchestrator.create_agent", return_value=mock_architect):
            result = await orchestrator.run_team_task("simple task")
        assert result.status == "success"
        mock_event_store.emit.assert_any_call(
            orchestrator._event_store.emit.call_args_list[0][0][0],
            "run_started",
            summary="simple task",
        )
        mock_event_store.finish_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_team_task_architect_returns_plan(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        plan_json = '{"analysis":"test","architecture_decisions":[],"subtasks":[{"agent":"frontend_dev","task":"do x","priority":"high","depends_on":[]}],"parallel_groups":[],"estimated_complexity":"low"}'
        mock_architect.run = AsyncMock(return_value=plan_json)
        mock_dev = MagicMock()
        mock_dev.run = AsyncMock(return_value="Frontend work done")
        mock_dev.role = "frontend_dev"

        call_count = 0
        def create_agent(role, project_path, read_only=False, run_id=None, event_store=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_architect
            return mock_dev

        with patch("orchestrator.create_agent", side_effect=create_agent):
            result = await orchestrator.run_team_task("build feature x")
        assert result.status == "success"
        mock_event_store.emit.assert_any_call(
            orchestrator._event_store.emit.call_args_list[0][0][0],
            "plan_created",
            agent="architect",
            payload={"analysis": "test", "architecture_decisions": [], "subtasks": [
                {"agent": "frontend_dev", "task": "do x", "priority": "high", "depends_on": []}
            ], "parallel_groups": [], "estimated_complexity": "low"},
        )

    @pytest.mark.asyncio
    async def test_run_team_task_emit_sequence(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        plan_json = '{"analysis":"t","architecture_decisions":[],"subtasks":[{"agent":"frontend_dev","task":"d","priority":"high","depends_on":[]}],"parallel_groups":[],"estimated_complexity":"low"}'
        mock_architect.run = AsyncMock(return_value=plan_json)
        mock_dev = MagicMock()
        mock_dev.run = AsyncMock(return_value="Done")
        mock_dev.role = "frontend_dev"

        call_count = 0
        def create_agent(role, project_path, read_only=False, run_id=None, event_store=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_architect
            return mock_dev

        with patch("orchestrator.create_agent", side_effect=create_agent):
            result = await orchestrator.run_team_task("task")

        assert result.status == "success"
        assert mock_event_store.create_run.called
        assert mock_event_store.finish_run.called
        mock_event_store.emit.assert_any_call(mock_event_store.emit.call_args_list[0][0][0],
                                              "run_started", summary="task")

    @pytest.mark.asyncio
    async def test_qa_in_plan_serial_skips_loop(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        plan_json = '{"analysis":"t","architecture_decisions":[],"subtasks":[' \
                    '{"agent":"qa_tester","task":"qa","priority":"high","depends_on":[]},' \
                    '{"agent":"frontend_dev","task":"dev","priority":"high","depends_on":[]}' \
                    '],"parallel_groups":[],"estimated_complexity":"low"}'
        mock_architect.run = AsyncMock(return_value=plan_json)
        mock_qa = MagicMock()
        mock_qa.run = AsyncMock(return_value="QA FAIL - needs fixes")
        mock_qa.role = "qa_tester"
        mock_dev = MagicMock()
        mock_dev.run = AsyncMock(return_value="Dev work")
        mock_dev.role = "frontend_dev"

        call_count = 0
        def create_agent(role, project_path, read_only=False, run_id=None, event_store=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_architect
            if role == "qa_tester":
                return mock_qa
            return mock_dev

        with patch("orchestrator.create_agent", side_effect=create_agent):
            result = await orchestrator.run_team_task("task with qa in plan")

        assert result.status == "success"
        loop_events = [c[0][2] for c in mock_event_store.emit.call_args_list
                       if len(c[0]) >= 3 and c[0][2] == "loop_iteration_started"]
        assert len(loop_events) == 0

    @pytest.mark.asyncio
    async def test_run_team_task_architect_fails(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        mock_architect.run = AsyncMock(side_effect=RuntimeError("architect crash"))
        with patch("orchestrator.create_agent", return_value=mock_architect):
            result = await orchestrator.run_team_task("doomed task")
        assert result.status == "error"
        mock_event_store.finish_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_finish_run_always_called_success(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        plan_json = '{"analysis":"t","architecture_decisions":[],"subtasks":[{"agent":"frontend_dev","task":"d","priority":"high","depends_on":[]}],"parallel_groups":[],"estimated_complexity":"low"}'
        mock_architect.run = AsyncMock(return_value=plan_json)
        mock_dev = MagicMock()
        mock_dev.run = AsyncMock(return_value="Done")
        mock_dev.role = "frontend_dev"

        call_count = 0
        def create_agent(role, project_path, read_only=False, run_id=None, event_store=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_architect
            return mock_dev

        with patch("orchestrator.create_agent", side_effect=create_agent):
            await orchestrator.run_team_task("test")
        assert mock_event_store.finish_run.call_count >= 1

    @pytest.mark.asyncio
    async def test_finish_run_always_called_error(self, orchestrator, mock_event_store):
        mock_architect = MagicMock()
        mock_architect.run = AsyncMock(side_effect=RuntimeError("fail"))
        with patch("orchestrator.create_agent", return_value=mock_architect):
            await orchestrator.run_team_task("doomed")
        assert mock_event_store.finish_run.call_count >= 1
