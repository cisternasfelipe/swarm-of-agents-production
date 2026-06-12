import re
from pathlib import Path
from typing import Literal

from config import ROLE_BOUNDARIES, GUARDRAILS_ENABLED, GUARDRAILS_STRICT_MODE
from utils.logger import get_logger

logger = get_logger("guardrails")

GuardrailResult = Literal["allow", "warn", "block"]


def validate_tool_call(role: str, tool_name: str, args: dict) -> tuple[GuardrailResult, str]:
    if not GUARDRAILS_ENABLED:
        return "allow", ""

    if tool_name not in ["mcp__filesystem__write_file", "mcp__filesystem__edit_file", "mcp__filesystem__create_directory", "mcp__filesystem__move_file"]:
        return "allow", ""

    path = args.get("path") or args.get("source") or args.get("destination")
    if not path:
        return "allow", ""

    path_obj = Path(path).resolve()
    boundaries = ROLE_BOUNDARIES.get(role, {})

    if not boundaries:
        return "allow", ""

    hard_blocked = boundaries.get("hard_blocked", [])
    for pattern in hard_blocked:
        if _matches_pattern(path_obj, pattern):
            message = f"Access denied: {path} is outside your scope as {role}"
            logger.warning(
                "guardrail_blocked",
                role=role,
                tool=tool_name,
                path=str(path_obj),
                pattern=pattern,
            )
            return "block", message

    soft_blocked = boundaries.get("soft_blocked", [])
    for pattern in soft_blocked:
        if _matches_pattern(path_obj, pattern):
            if GUARDRAILS_STRICT_MODE:
                message = f"Access denied: {path} is outside your scope as {role}"
                logger.warning(
                    "guardrail_blocked_strict",
                    role=role,
                    tool=tool_name,
                    path=str(path_obj),
                    pattern=pattern,
                )
                return "block", message
            else:
                logger.info(
                    "guardrail_warned",
                    role=role,
                    tool=tool_name,
                    path=str(path_obj),
                    pattern=pattern,
                )
                return "warn", f"Warning: {path} is outside your typical scope as {role}"

    return "allow", ""


def _matches_pattern(path: Path, pattern: str) -> bool:
    path_str = str(path)

    if pattern.startswith("**/"):
        suffix = pattern[3:]
        return path_str.endswith(suffix) or f"/{suffix}" in path_str

    if pattern.endswith("/"):
        return f"/{pattern}" in path_str or path_str.endswith(f"/{pattern[:-1]}")

    if "*" in pattern:
        regex = pattern.replace("*", ".*")
        return bool(re.search(regex, path_str))

    return pattern in path_str
