import pytest
from unittest.mock import MagicMock

from rag.retriever import Retriever


class TestStoreOperations:
    @pytest.fixture
    def retriever(self, mock_knowledge_base, mock_embedder):
        return Retriever(kb=mock_knowledge_base, embedder=mock_embedder)

    def test_store_decision(self, retriever, mock_knowledge_base):
        retriever.store_decision("/proj", "content", agent_role="architect")
        args, kwargs = mock_knowledge_base.store.call_args
        assert kwargs["metadata"]["type"] == "decision"
        assert kwargs["metadata"]["agent"] == "architect"

    def test_store_bug_composes_content(self, retriever, mock_knowledge_base):
        retriever.store_bug("/proj", "login broken", "add try/catch", agent_role="backend_dev")
        args, kwargs = mock_knowledge_base.store.call_args
        assert "Bug: login broken" in kwargs["content"]
        assert "Solution: add try/catch" in kwargs["content"]
        assert kwargs["metadata"]["type"] == "bug"

    def test_store_pattern(self, retriever, mock_knowledge_base):
        retriever.store_pattern("/proj", "use repository pattern", agent_role="architect")
        args, kwargs = mock_knowledge_base.store.call_args
        assert kwargs["metadata"]["type"] == "pattern"

    def test_store_with_file_path(self, retriever, mock_knowledge_base):
        retriever.store_decision("/proj", "content", agent_role="architect", file_path="/proj/main.py")
        args, kwargs = mock_knowledge_base.store.call_args
        assert kwargs["metadata"]["file"] == "/proj/main.py"


class TestRetrieve:
    @pytest.fixture
    def retriever(self, mock_knowledge_base, mock_embedder):
        return Retriever(kb=mock_knowledge_base, embedder=mock_embedder)

    def test_retrieve_no_filter(self, retriever, mock_knowledge_base):
        mock_knowledge_base.query.return_value = []
        result = retriever.retrieve("/proj", "query")
        assert result == []

    def test_retrieve_with_doc_type_filter(self, retriever, mock_knowledge_base):
        retriever.retrieve("/proj", "query", doc_type="bug")
        mock_knowledge_base.query.assert_called_once()
        called_where = mock_knowledge_base.query.call_args[1].get("where")
        assert called_where == {"type": "bug"}

    def test_retrieve_defaults_n_results(self, retriever, mock_knowledge_base):
        retriever.retrieve("/proj", "query")
        assert mock_knowledge_base.query.call_args[1]["n_results"] == 5


class TestGetContext:
    @pytest.fixture
    def retriever(self, mock_knowledge_base, mock_embedder):
        return Retriever(kb=mock_knowledge_base, embedder=mock_embedder)

    def test_empty_results(self, retriever, mock_knowledge_base):
        mock_knowledge_base.query.return_value = []
        ctx = retriever.get_context("/proj", "query")
        assert ctx == ""

    def test_formats_results(self, retriever, mock_knowledge_base):
        mock_knowledge_base.query.return_value = [
            {"content": "Use factory pattern", "metadata": {"type": "pattern", "agent": "architect"}, "distance": 0.1},
        ]
        ctx = retriever.get_context("/proj", "patterns")
        assert "[pattern by architect]" in ctx
        assert "Use factory pattern" in ctx

    def test_missing_metadata_keys(self, retriever, mock_knowledge_base):
        mock_knowledge_base.query.return_value = [
            {"content": "content", "distance": 0.1},
        ]
        ctx = retriever.get_context("/proj", "query")
        assert "[unknown by unknown]" in ctx
        assert "content" in ctx

    def test_multiple_results_separated(self, retriever, mock_knowledge_base):
        mock_knowledge_base.query.return_value = [
            {"content": "A", "metadata": {"type": "bug", "agent": "qa"}, "distance": 0.1},
            {"content": "B", "metadata": {"type": "pattern", "agent": "architect"}, "distance": 0.2},
        ]
        ctx = retriever.get_context("/proj", "query")
        assert "---" in ctx
        assert "A" in ctx
        assert "B" in ctx
