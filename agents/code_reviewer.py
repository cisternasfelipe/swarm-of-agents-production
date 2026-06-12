from agents.base_agent import BaseAgent


class CodeReviewerAgent(BaseAgent):
    role = "code_reviewer"
    prompt_file = "code_reviewer.md"
