from agents.base_agent import BaseAgent


class QATesterAgent(BaseAgent):
    role = "qa_tester"
    prompt_file = "qa_tester.md"
