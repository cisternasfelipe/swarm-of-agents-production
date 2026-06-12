from agents.base_agent import BaseAgent
from agents.architect import ArchitectAgent
from agents.backend_dev import BackendDevAgent
from agents.frontend_dev import FrontendDevAgent
from agents.qa_tester import QATesterAgent
from agents.devops import DevOpsAgent
from agents.code_reviewer import CodeReviewerAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "architect": ArchitectAgent,
    "backend_dev": BackendDevAgent,
    "frontend_dev": FrontendDevAgent,
    "qa_tester": QATesterAgent,
    "devops": DevOpsAgent,
    "code_reviewer": CodeReviewerAgent,
}


def create_agent(role: str, project_path: str, read_only: bool = False,
                 run_id: str | None = None, event_store=None) -> BaseAgent:
    cls = AGENT_REGISTRY.get(role)
    if cls is None:
        raise ValueError(f"Unknown agent role: {role}")
    return cls(project_path=project_path, read_only=read_only,
               run_id=run_id, event_store=event_store)
