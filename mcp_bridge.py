import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from orchestrator import Orchestrator
from rag.knowledge_base import KnowledgeBase
from rag.embedder import Embedder
from rag.retriever import Retriever
from utils.logger import get_logger
from utils.metrics import Metrics
from config import DEEPSEEK_API_KEY

logger = get_logger("mcp_bridge")
server = Server("agentscope-swarm")
_kb = KnowledgeBase()
_embedder = Embedder()
_retriever = Retriever(_kb, _embedder)
_metrics = Metrics()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="run_team_task",
            description=(
                "Run a full team workflow: Architect analyzes the task, "
                "assigns it to developers (backend/frontend), QA tests it, "
                "and Code Reviewer reviews it. Loops up to 3 times if issues are found. "
                "Use this for complex tasks that benefit from team collaboration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task description to execute",
                    },
                    "directory": {
                        "type": "string",
                        "description": "The project working directory",
                    },
                },
                "required": ["task", "directory"],
            },
        ),
        Tool(
            name="delegate_task",
            description=(
                "Delegate a task to a specific agent role. "
                "Available roles: architect, backend_dev, frontend_dev, "
                "qa_tester, devops, code_reviewer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task description",
                    },
                    "role": {
                        "type": "string",
                        "enum": [
                            "architect",
                            "backend_dev",
                            "frontend_dev",
                            "qa_tester",
                            "devops",
                            "code_reviewer",
                        ],
                        "description": "The agent role to delegate to",
                    },
                    "directory": {
                        "type": "string",
                        "description": "The project working directory",
                    },
                },
                "required": ["task", "role", "directory"],
            },
        ),
        Tool(
            name="query_knowledge",
            description=(
                "Query the project knowledge base (RAG) for context, "
                "decisions, bugs, and patterns stored by the team agents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "The project path",
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "doc_type": {
                        "type": "string",
                        "enum": ["decision", "bug", "pattern"],
                        "description": "Filter by document type (optional)",
                    },
                },
                "required": ["project", "query"],
            },
        ),
        Tool(
            name="health_check",
            description="Check the health of the AgentScope swarm system.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if not DEEPSEEK_API_KEY:
        return [TextContent(type="text", text="Error: DEEPSEEK_API_KEY not set in .env")]

    if name == "run_team_task":
        return await _handle_team_task(arguments)
    elif name == "delegate_task":
        return await _handle_delegate(arguments)
    elif name == "query_knowledge":
        return _handle_query(arguments)
    elif name == "health_check":
        return _handle_health()
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_team_task(args: dict) -> list[TextContent]:
    task = args["task"]
    directory = args["directory"]
    orchestrator = Orchestrator(project_path=directory)
    result = await orchestrator.run_team_task(task)
    return [TextContent(type="text", text=result.output)]


async def _handle_delegate(args: dict) -> list[TextContent]:
    task = args["task"]
    role = args["role"]
    directory = args["directory"]
    orchestrator = Orchestrator(project_path=directory)
    result = await orchestrator.delegate_task(task, role)
    return [TextContent(type="text", text=result.output)]


def _handle_query(args: dict) -> list[TextContent]:
    project = args["project"]
    query = args["query"]
    doc_type = args.get("doc_type")
    results = _retriever.retrieve(project, query, n_results=5, doc_type=doc_type)
    if not results:
        return [TextContent(type="text", text="No results found in knowledge base.")]
    output = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        output.append(
            f"### Result {i}\n"
            f"- Type: {meta.get('type', 'unknown')}\n"
            f"- Agent: {meta.get('agent', 'unknown')}\n"
            f"- Distance: {r.get('distance', 'N/A')}\n\n"
            f"{r['content']}\n"
        )
    return [TextContent(type="text", text="\n---\n".join(output))]


def _handle_health() -> list[TextContent]:
    checks = {"deepseek_api": bool(DEEPSEEK_API_KEY)}
    try:
        _kb.list_projects()
        checks["chromadb"] = True
    except Exception as e:
        checks["chromadb"] = f"Error: {e}"
    summary = _metrics.get_summary()
    output = "## Health Check\n\n"
    for k, v in checks.items():
        status = "OK" if v is True else f"FAIL: {v}" if v is not False else "NOT CONFIGURED"
        output += f"- {k}: {status}\n"
    output += f"\n## Metrics\n```json\n{summary}\n```"
    return [TextContent(type="text", text=output)]


async def main():
    logger.info("mcp_bridge_starting")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
