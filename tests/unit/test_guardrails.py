import pytest
from pathlib import Path
from utils.guardrails import validate_tool_call, _matches_pattern


class TestValidateToolCall:
    def test_allow_frontend_writes_jsx(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/components/Button.jsx"},
        )
        assert result == "allow"
        assert msg == ""

    def test_block_frontend_writes_api(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "block"
        assert "Access denied" in msg
        assert "frontend_dev" in msg

    def test_warn_frontend_writes_config(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/config.py"},
        )
        assert result == "warn"
        assert "Warning" in msg

    def test_strict_mode_upgrades_warn_to_block(self, monkeypatch):
        monkeypatch.setattr("utils.guardrails.GUARDRAILS_STRICT_MODE", True)
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/config.py"},
        )
        assert result == "block"

    def test_disabled_guardrails_allows_all(self, monkeypatch):
        monkeypatch.setattr("utils.guardrails.GUARDRAILS_ENABLED", False)
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "allow"

    def test_read_tool_always_allowed(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__read_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "allow"

    def test_no_path_in_args(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"content": "hello"},
        )
        assert result == "allow"

    def test_role_without_boundaries(self):
        result, msg = validate_tool_call(
            "architect",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "allow"

    def test_backend_blocked_from_components(self):
        result, msg = validate_tool_call(
            "backend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/components/Header.jsx"},
        )
        assert result == "block"

    def test_backend_warned_on_html_template(self):
        result, msg = validate_tool_call(
            "backend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/templates/index.html"},
        )
        assert result == "warn"

    def test_qa_tester_blocked_from_src(self):
        result, msg = validate_tool_call(
            "qa_tester",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "block"

    def test_devops_blocked_from_app_code(self):
        result, msg = validate_tool_call(
            "devops",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/app.py"},
        )
        assert result == "block"

    def test_edit_file_also_validated(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__edit_file",
            {"path": "/proj/src/api/users.py"},
        )
        assert result == "block"

    def test_create_directory_validated(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__create_directory",
            {"path": "/proj/src/api/v2"},
        )
        assert result == "block"

    def test_move_file_validated(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__move_file",
            {"source": "/proj/src/api/users.py"},
        )
        assert result == "block"

    def test_source_arg_used_for_path(self):
        result, msg = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__move_file",
            {"source": "/proj/src/components/Button.jsx"},
        )
        assert result == "allow"


class TestMatchesPattern:
    def test_double_star_prefix(self):
        assert _matches_pattern(Path("/a/b/api/users.py"), "**/api/")

    def test_double_star_no_match(self):
        assert not _matches_pattern(Path("/a/b/components/Button.jsx"), "**/api/")

    def test_double_star_empty_suffix(self):
        assert _matches_pattern(Path("/anything"), "**/")

    def test_trailing_slash(self):
        assert _matches_pattern(Path("/proj/src/components/"), "components/")

    def test_trailing_slash_no_match(self):
        assert not _matches_pattern(Path("/proj/src/api/"), "components/")

    def test_plain_substring(self):
        assert _matches_pattern(Path("/proj/config.py"), "config")
        assert not _matches_pattern(Path("/proj/app.py"), "config")

    def test_glob_pattern(self):
        assert _matches_pattern(Path("/proj/docker-compose.yml"), "docker-compose*")
        assert not _matches_pattern(Path("/proj/Dockerfile"), "docker-compose*")

    def test_empty_string_pattern(self):
        assert _matches_pattern(Path("/proj/app.py"), "")

    def test_multiple_patterns_first_wins_hard(self):
        result, _ = validate_tool_call(
            "frontend_dev",
            "mcp__filesystem__write_file",
            {"path": "/proj/src/api/config.py"},
        )
        assert result == "block"
