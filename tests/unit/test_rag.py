import pytest
from unittest.mock import MagicMock

from rag.knowledge_base import KnowledgeBase
from rag.embedder import Embedder


class TestKnowledgeBase:
    @pytest.fixture
    def kb(self, tmp_chroma_path):
        return KnowledgeBase()

    def test_get_collection_name_deterministic(self, kb):
        name1 = kb._get_collection_name("/tmp/project-a")
        name2 = kb._get_collection_name("/tmp/project-a")
        assert name1 == name2

    def test_get_collection_name_different_projects(self, kb):
        name1 = kb._get_collection_name("/tmp/proj-a")
        name2 = kb._get_collection_name("/tmp/proj-b")
        assert name1 != name2

    def test_list_projects_empty_initially(self, kb):
        projects = kb.list_projects()
        assert isinstance(projects, list)


class TestEmbedderSingleton:
    def teardown_method(self):
        Embedder._instance = None
        try:
            Embedder._model = None
        except AttributeError:
            pass

    def test_singleton_same_instance(self):
        e1 = Embedder()
        e2 = Embedder()
        assert e1 is e2

    def test_reset_singleton(self):
        e1 = Embedder()
        Embedder._instance = None
        e2 = Embedder()
        assert e1 is not e2
