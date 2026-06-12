import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pydantic import SecretStr

from agentscope.agent import Agent
from agentscope.model import DeepSeekChatModel
from agentscope.model._deepseek import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.event import (
    TextBlockDeltaEvent,
    RequireUserConfirmEvent,
    UserConfirmResultEvent,
    ConfirmResult,
)
from agentscope.mcp import MCPClient, StdioMCPConfig

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    PROMPTS_DIR,
    FILESYSTEM_MCP_COMMAND,
    FILESYSTEM_MCP_ARGS,
    FILESYSTEM_READ_ONLY_TOOLS,
    SKILLS_DIR,
    SKILLS_BY_ROLE,
    SKILLS_GLOBAL,
)
from rag.knowledge_base import KnowledgeBase
from rag.embedder import Embedder
from rag.retriever import Retriever
from utils.rate_limiter import RateLimiter
from utils.logger import get_logger
from utils.metrics import Metrics
from utils.guardrails import validate_tool_call


class BaseAgent(ABC):
    role: str = ""
    prompt_file: str = ""

    def __init__(self, project_path: str, read_only: bool = False,
                 run_id: str | None = None, event_store=None):
        self.project_path = project_path
        self.read_only = read_only
        self._run_id = run_id
        self._event_store = event_store
        self._kb = KnowledgeBase()
        self._embedder = Embedder()
        self._retriever = Retriever(self._kb, self._embedder)
        self._rate_limiter = RateLimiter()
        self._logger = get_logger(self.role)
        self._metrics = Metrics()
        self._agent: Optional[Agent] = None
        self._mcp_client: Optional[MCPClient] = None

    def _load_prompt(self) -> str:
        prompt_path = PROMPTS_DIR / self.prompt_file
        base_prompt = prompt_path.read_text() if prompt_path.exists() else f"You are a {self.role}."
        rag_context = self._retriever.get_context(self.project_path, self.role, n_results=5)
        if rag_context:
            base_prompt += f"\n\n## Project Context (from knowledge base)\n{rag_context}"
        base_prompt += f"\n\n## Current Project\nWorking directory: {self.project_path}"
        return base_prompt

    def _build_tools(self) -> list:
        from agentscope.tool import Bash

        tools = []
        if not self.read_only:
            tools.append(Bash())
        return tools

    def _get_mcp_enable_tools(self) -> Optional[list[str]]:
        if self.read_only:
            return FILESYSTEM_READ_ONLY_TOOLS
        return None

    def _load_skills(self) -> list:
        skill_paths = []
        for skill_name in SKILLS_GLOBAL:
            path = SKILLS_DIR / skill_name
            if path.is_dir() and (path / "SKILL.md").exists():
                skill_paths.append(str(path))
        for skill_name in SKILLS_BY_ROLE.get(self.role, []):
            path = SKILLS_DIR / skill_name
            if path.is_dir() and (path / "SKILL.md").exists():
                skill_paths.append(str(path))
        return skill_paths

    async def _ensure_agent(self):
        if self._agent is not None:
            return

        from agentscope.tool import Toolkit

        self._mcp_client = MCPClient(
            name="filesystem",
            is_stateful=True,
            mcp_config=StdioMCPConfig(
                command=FILESYSTEM_MCP_COMMAND,
                args=[*FILESYSTEM_MCP_ARGS, self.project_path],
            ),
            enable_tools=self._get_mcp_enable_tools(),
        )
        await self._mcp_client.connect()

        credential = DeepSeekCredential(api_key=SecretStr(DEEPSEEK_API_KEY))
        model = DeepSeekChatModel(
            credential=credential,
            model=DEEPSEEK_MODEL,
            stream=True,
        )
        self._agent = Agent(
            name=self.role,
            system_prompt=self._load_prompt(),
            model=model,
            toolkit=Toolkit(
                tools=self._build_tools(),
                mcps=[self._mcp_client],
                skills_or_loaders=self._load_skills(),
            ),
        )

    async def _cleanup(self):
        if self._mcp_client is not None:
            try:
                await self._mcp_client.close()
            except Exception:
                pass
            self._mcp_client = None

    async def run(self, task: str) -> str:
        self._rate_limiter.wait()
        start = time.time()
        self._logger.info("task_start", role=self.role, task=task[:100])

        if self._event_store and self._run_id:
            self._event_store.emit(self._run_id, "agent_started", agent=self.role)

        try:
            await self._ensure_agent()
            result_parts = []
            stream_input = UserMsg("user", task)
            
            while True:
                confirm_event = None
                async for event in self._agent.reply_stream(stream_input):
                    if isinstance(event, TextBlockDeltaEvent):
                        result_parts.append(event.delta)
                    elif isinstance(event, RequireUserConfirmEvent):
                        confirm_event = event
                        break
                
                if confirm_event is None:
                    break

                confirm_results = []
                for tc in confirm_event.tool_calls:
                    try:
                        args_dict = json.loads(tc.input) if isinstance(tc.input, str) else tc.input
                    except json.JSONDecodeError:
                        args_dict = {}

                    result, message = validate_tool_call(self.role, tc.name, args_dict)

                    if result == "block":
                        confirm_results.append(ConfirmResult(confirmed=False, tool_call=tc))
                        self._metrics.record_guardrail_violation(self.role, "block")
                        if self._event_store and self._run_id:
                            self._event_store.emit(self._run_id, "guardrail_triggered",
                                                   agent=self.role,
                                                   payload={"tool": tc.name, "path": args_dict.get("path"),
                                                            "result": "block", "message": message})
                        self._logger.warning(
                            "guardrail_blocked",
                            role=self.role,
                            tool=tc.name,
                            message=message,
                        )
                    elif result == "warn":
                        confirm_results.append(ConfirmResult(confirmed=True, tool_call=tc))
                        self._metrics.record_guardrail_violation(self.role, "warn")
                        if self._event_store and self._run_id:
                            self._event_store.emit(self._run_id, "guardrail_triggered",
                                                   agent=self.role,
                                                   payload={"tool": tc.name, "path": args_dict.get("path"),
                                                            "result": "warn", "message": message})
                        self._logger.info(
                            "guardrail_warned",
                            role=self.role,
                            tool=tc.name,
                            message=message,
                        )
                    else:
                        confirm_results.append(ConfirmResult(confirmed=True, tool_call=tc))
                        if self._event_store and self._run_id:
                            self._event_store.emit(self._run_id, "tool_call_confirmed",
                                                   agent=self.role,
                                                   payload={"tool": tc.name, "path": args_dict.get("path")})

                stream_input = UserConfirmResultEvent(
                    reply_id=confirm_event.reply_id,
                    confirm_results=confirm_results,
                )
            
            result = "".join(result_parts)
            duration_ms = int((time.time() - start) * 1000)
            self._metrics.record_agent_call(self.role, duration_ms=duration_ms)
            self._logger.info("task_done", role=self.role, duration_ms=duration_ms)
            self._store_knowledge(task, result)

            if self._event_store and self._run_id:
                self._event_store.emit(self._run_id, "agent_finished", agent=self.role,
                                       summary=result[:500])

            return result
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            self._logger.error("task_failed", role=self.role, error=str(e), duration_ms=duration_ms)
            if self._event_store and self._run_id:
                self._event_store.emit(self._run_id, "agent_failed", agent=self.role,
                                       summary=str(e)[:500])
            raise
        finally:
            await self._cleanup()

    def _store_knowledge(self, task: str, result: str):
        try:
            if "bug" in task.lower() or "fix" in task.lower():
                self._retriever.store_bug(
                    self.project_path,
                    description=task[:200],
                    solution=result[:500],
                    agent_role=self.role,
                )
            elif "pattern" in task.lower() or "architecture" in task.lower():
                self._retriever.store_pattern(
                    self.project_path,
                    pattern=result[:500],
                    agent_role=self.role,
                )
            else:
                self._retriever.store_decision(
                    self.project_path,
                    content=f"Task: {task[:200]}\nResult: {result[:500]}",
                    agent_role=self.role,
                )
        except Exception:
            pass
