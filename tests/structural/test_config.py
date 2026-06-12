import pytest
from config import (
    AGENT_ROLES,
    SKILLS_BY_ROLE,
    SKILLS_DIR,
    SKILLS_GLOBAL,
    ROLE_BOUNDARIES,
    MAX_LOOP_ITERATIONS,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
)
from observability import EVENT_TYPES


class TestRoleBoundariesCoverage:
    def test_dev_roles_have_boundaries(self):
        assert "frontend_dev" in ROLE_BOUNDARIES
        assert "backend_dev" in ROLE_BOUNDARIES
        assert "qa_tester" in ROLE_BOUNDARIES
        assert "devops" in ROLE_BOUNDARIES

    def test_readonly_roles_excluded_intentionally(self):
        assert "architect" not in ROLE_BOUNDARIES
        assert "code_reviewer" not in ROLE_BOUNDARIES

    def test_skills_by_role_maps_to_agents(self):
        for role in SKILLS_BY_ROLE:
            assert role in AGENT_ROLES, f"SKILLS_BY_ROLE maps to unknown role: {role}"

    def test_skill_directories_exist(self):
        for skill_name in SKILLS_GLOBAL:
            path = SKILLS_DIR / skill_name
            assert path.is_dir(), f"Global skill dir missing: {path}"
        for role_skills in SKILLS_BY_ROLE.values():
            for skill_name in role_skills:
                path = SKILLS_DIR / skill_name
                assert path.is_dir(), f"Skill dir missing: {path}"


class TestSafeConstants:
    def test_max_loop_iterations_positive(self):
        assert MAX_LOOP_ITERATIONS > 0

    def test_rate_limit_positive(self):
        assert RATE_LIMIT_REQUESTS_PER_MINUTE > 0

    def test_event_types_completeness(self):
        emitted_types = {
            "run_started", "run_finished", "plan_created",
            "agent_started", "agent_finished", "agent_failed",
            "loop_iteration_started", "qa_verdict", "review_verdict",
            "fix_requested", "tool_call_confirmed", "guardrail_triggered",
        }
        for t in emitted_types:
            assert t in EVENT_TYPES, f"Missing from EVENT_TYPES: {t}"
