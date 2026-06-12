import pytest
from pathlib import Path
from config import PROMPTS_DIR, AGENT_ROLES


class TestPromptFiles:
    def test_all_prompt_files_exist(self):
        for role in AGENT_ROLES:
            path = PROMPTS_DIR / f"{role}.md"
            assert path.exists(), f"Missing prompt: {path}"

    def test_all_prompt_files_non_empty(self):
        for role in AGENT_ROLES:
            path = PROMPTS_DIR / f"{role}.md"
            content = path.read_text()
            assert len(content) > 50, f"Prompt too short: {path} ({len(content)} chars)"

    def test_prompt_files_match_agents(self):
        md_files = list(PROMPTS_DIR.glob("*.md"))
        md_roles = {f.stem for f in md_files}
        agent_roles = set(AGENT_ROLES.keys())
        assert md_roles == agent_roles, f"Mismatch: md={md_roles - agent_roles}, agents={agent_roles - md_roles}"
