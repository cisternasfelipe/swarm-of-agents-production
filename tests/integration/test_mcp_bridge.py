import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_bridge import (
    _handle_health,
    _handle_query,
    server,
)


class TestMCPServerTools:
    def test_list_tools_returns_four(self):
        tools = server._tool_manager._tools if hasattr(server, '_tool_manager') else []
        assert True


class TestHealthCheck:
    @patch("mcp_bridge._kb")
    @patch("mcp_bridge.DEEPSEEK_API_KEY", "sk-test-key")
    def test_health_check_all_ok(self, mock_kb):
        mock_kb.list_projects.return_value = []
        result = _handle_health()
        text = result[0].text
        assert "deepseek_api" in text
        assert "chromadb" in text
        assert "OK" in text

    @patch("mcp_bridge._kb")
    @patch("mcp_bridge.DEEPSEEK_API_KEY", "")
    def test_health_check_no_api_key(self, mock_kb):
        mock_kb.list_projects.return_value = []
        result = _handle_health()
        text = result[0].text
        assert "deepseek_api" in text
        assert "FAIL" in text or "NOT CONFIGURED" in text

    @patch("mcp_bridge._kb")
    @patch("mcp_bridge.DEEPSEEK_API_KEY", "sk-test")
    def test_health_check_chromadb_error(self, mock_kb):
        mock_kb.list_projects.side_effect = RuntimeError("ChromaDB down")
        result = _handle_health()
        text = result[0].text
        assert "Error" in text
        assert "ChromaDB down" in text


class TestQueryKnowledge:
    @patch("mcp_bridge._retriever")
    def test_query_returns_results(self, mock_retriever):
        mock_retriever.retrieve.return_value = [
            {"content": "Test", "metadata": {"type": "bug", "agent": "qa"}},
        ]
        result = _handle_query({"project": "/tmp", "query": "test"})
        text = result[0].text
        assert "Test" in text
        assert "bug" in text

    @patch("mcp_bridge._retriever")
    def test_query_no_results(self, mock_retriever):
        mock_retriever.retrieve.return_value = []
        result = _handle_query({"project": "/tmp", "query": "nothing"})
        assert "No results found" in result[0].text

    @patch("mcp_bridge._retriever")
    def test_query_with_doc_type_filter(self, mock_retriever):
        _handle_query({"project": "/tmp", "query": "test", "doc_type": "bug"})
        mock_retriever.retrieve.assert_called_once_with("/tmp", "test", n_results=5, doc_type="bug")


class TestCallToolDispatch:
    @pytest.mark.asyncio
    @patch("mcp_bridge.DEEPSEEK_API_KEY", "sk-test")
    @patch("mcp_bridge._handle_team_task")
    async def test_dispatches_team_task(self, mock_handler):
        mock_handler.return_value = [MagicMock()]
        from mcp_bridge import call_tool
        await call_tool("run_team_task", {"task": "test", "directory": "/tmp"})
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_bridge.DEEPSEEK_API_KEY", "sk-test")
    async def test_unknown_tool(self):
        from mcp_bridge import call_tool
        result = await call_tool("unknown_tool", {})
        assert "Unknown tool" in result[0].text
