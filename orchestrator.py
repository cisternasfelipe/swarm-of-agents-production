import asyncio
import json
from typing import Optional

from agents import create_agent
from config import MAX_LOOP_ITERATIONS
from utils.logger import get_logger
from utils.metrics import Metrics

logger = get_logger("orchestrator")
metrics = Metrics()


class TaskResult:
    def __init__(self, status: str, output: str, agent: str = "", details: dict = None):
        self.status = status
        self.output = output
        self.agent = agent
        self.details = details or {}


class Orchestrator:
    def __init__(self, project_path: str, read_only: bool = False):
        self.project_path = project_path
        self.read_only = read_only
        self._active_tasks = {}

    async def run_team_task(self, task: str) -> TaskResult:
        logger.info("team_task_start", task=task[:100])
        try:
            architect = create_agent("architect", self.project_path, read_only=True)
            plan_result = await architect.run(
                f"Analyze this task and create an execution plan:\n\n{task}"
            )
            plan = self._parse_plan(plan_result)
            if not plan or not plan.get("subtasks"):
                return TaskResult("success", plan_result, "architect")

            results = {}
            for group in plan.get("parallel_groups", []):
                group_tasks = [
                    st for st in plan["subtasks"] if st["agent"] in group
                ]
                group_results = await self._run_parallel(group_tasks)
                results.update(group_results)

            remaining = [
                st for st in plan["subtasks"]
                if st["agent"] not in [a for g in plan.get("parallel_groups", []) for a in g]
            ]
            for subtask in remaining:
                result = await self._run_single(subtask)
                results[subtask["agent"]] = result

            qa_needed = any(st["agent"] == "qa_tester" for st in plan["subtasks"])
            review_needed = any(st["agent"] == "code_reviewer" for st in plan["subtasks"])

            if qa_needed or review_needed:
                for iteration in range(MAX_LOOP_ITERATIONS):
                    logger.info("loop_iteration", iteration=iteration + 1)
                    if qa_needed and "qa_tester" not in results:
                        qa_agent = create_agent("qa_tester", self.project_path, read_only=self.read_only)
                        qa_result = await qa_agent.run(
                            f"Test the implementation for this task:\n\n{task}\n\n"
                            f"Results so far:\n{self._summarize_results(results)}"
                        )
                        results["qa_tester"] = qa_result
                        if "FAIL" in qa_result or "NEEDS_FIX" in qa_result:
                            dev_tasks = [st for st in plan["subtasks"] if "dev" in st["agent"]]
                            for dt in dev_tasks:
                                fix_result = await self._run_single({
                                    "agent": dt["agent"],
                                    "task": f"Fix issues found by QA:\n{qa_result}\n\nOriginal task: {dt['task']}"
                                })
                                results[dt["agent"]] = fix_result
                            results.pop("qa_tester", None)
                            continue

                    if review_needed and "code_reviewer" not in results:
                        reviewer = create_agent("code_reviewer", self.project_path, read_only=True)
                        review_result = await reviewer.run(
                            f"Review the code changes for this task:\n\n{task}\n\n"
                            f"Results so far:\n{self._summarize_results(results)}"
                        )
                        results["code_reviewer"] = review_result
                        if "REQUEST_CHANGES" in review_result:
                            dev_tasks = [st for st in plan["subtasks"] if "dev" in st["agent"]]
                            for dt in dev_tasks:
                                fix_result = await self._run_single({
                                    "agent": dt["agent"],
                                    "task": f"Address review comments:\n{review_result}\n\nOriginal task: {dt['task']}"
                                })
                                results[dt["agent"]] = fix_result
                            results.pop("code_reviewer", None)
                            continue
                    break

            final_output = self._compile_results(task, plan, results)
            metrics.record_task(success=True)
            logger.info("team_task_done", status="success")
            return TaskResult("success", final_output, "orchestrator", results)

        except Exception as e:
            metrics.record_task(success=False)
            logger.error("team_task_failed", error=str(e))
            return TaskResult("error", f"Task failed: {str(e)}", "orchestrator")

    async def delegate_task(self, task: str, role: str) -> TaskResult:
        logger.info("delegate_start", role=role, task=task[:100])
        try:
            agent = create_agent(role, self.project_path, read_only=self.read_only)
            result = await agent.run(task)
            logger.info("delegate_done", role=role)
            return TaskResult("success", result, role)
        except Exception as e:
            logger.error("delegate_failed", role=role, error=str(e))
            return TaskResult("error", f"Agent {role} failed: {str(e)}", role)

    async def _run_parallel(self, subtasks: list[dict]) -> dict[str, str]:
        tasks = []
        for st in subtasks:
            tasks.append(self._run_single(st))
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        results = {}
        for st, res in zip(subtasks, results_list):
            if isinstance(res, Exception):
                results[st["agent"]] = f"Error: {str(res)}"
            else:
                results[st["agent"]] = res
        return results

    async def _run_single(self, subtask: dict) -> str:
        agent = create_agent(subtask["agent"], self.project_path, read_only=self.read_only)
        return await agent.run(subtask["task"])

    def _parse_plan(self, plan_text: str) -> Optional[dict]:
        try:
            start = plan_text.find("{")
            end = plan_text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(plan_text[start:end])
        except json.JSONDecodeError:
            logger.warning("plan_parse_failed")
        return None

    def _summarize_results(self, results: dict) -> str:
        parts = []
        for agent, result in results.items():
            parts.append(f"### {agent}\n{result[:500]}")
        return "\n\n".join(parts)

    def _compile_results(self, task: str, plan: dict, results: dict) -> str:
        output = f"# Task: {task}\n\n"
        output += f"## Plan\n{plan.get('analysis', 'N/A')}\n\n"
        output += "## Architecture Decisions\n"
        for d in plan.get("architecture_decisions", []):
            output += f"- {d}\n"
        output += "\n## Results\n"
        for agent, result in results.items():
            output += f"\n### {agent}\n{result}\n"
        return output
