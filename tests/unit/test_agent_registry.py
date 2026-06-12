import pytest
from agents import AGENT_REGISTRY, create_agent, BaseAgent
from agents.architect import ArchitectAgent
from agents.backend_dev import BackendDevAgent
from agents.frontend_dev import FrontendDevAgent
from agents.qa_tester import QATesterAgent
from agents.devops import DevOpsAgent
from agents.code_reviewer import CodeReviewerAgent


class TestAgentRegistry:
    def test_all_six_roles_registered(self):
        assert len(AGENT_REGISTRY) == 6
        assert "architect" in AGENT_REGISTRY
        assert "backend_dev" in AGENT_REGISTRY
        assert "frontend_dev" in AGENT_REGISTRY
        assert "qa_tester" in AGENT_REGISTRY
        assert "devops" in AGENT_REGISTRY
        assert "code_reviewer" in AGENT_REGISTRY

    def test_create_agent_unknown_role_raises(self):
        with pytest.raises(ValueError, match="Unknown agent role"):
            create_agent("unknown_role", "/tmp")

    def test_registry_class_mapping(self):
        assert AGENT_REGISTRY["architect"] is ArchitectAgent
        assert AGENT_REGISTRY["backend_dev"] is BackendDevAgent
        assert AGENT_REGISTRY["frontend_dev"] is FrontendDevAgent
        assert AGENT_REGISTRY["qa_tester"] is QATesterAgent
        assert AGENT_REGISTRY["devops"] is DevOpsAgent
        assert AGENT_REGISTRY["code_reviewer"] is CodeReviewerAgent


class TestAgentClassAttributes:
    def test_architect_role_and_prompt(self):
        assert ArchitectAgent.role == "architect"
        assert ArchitectAgent.prompt_file == "architect.md"

    def test_backend_role_and_prompt(self):
        assert BackendDevAgent.role == "backend_dev"
        assert BackendDevAgent.prompt_file == "backend_dev.md"

    def test_frontend_role_and_prompt(self):
        assert FrontendDevAgent.role == "frontend_dev"
        assert FrontendDevAgent.prompt_file == "frontend_dev.md"

    def test_qa_role_and_prompt(self):
        assert QATesterAgent.role == "qa_tester"
        assert QATesterAgent.prompt_file == "qa_tester.md"

    def test_devops_role_and_prompt(self):
        assert DevOpsAgent.role == "devops"
        assert DevOpsAgent.prompt_file == "devops.md"

    def test_reviewer_role_and_prompt(self):
        assert CodeReviewerAgent.role == "code_reviewer"
        assert CodeReviewerAgent.prompt_file == "code_reviewer.md"

    def test_all_subclass_base_agent(self):
        for cls in [ArchitectAgent, BackendDevAgent, FrontendDevAgent,
                     QATesterAgent, DevOpsAgent, CodeReviewerAgent]:
            assert issubclass(cls, BaseAgent), f"{cls.__name__} is not a BaseAgent subclass"
