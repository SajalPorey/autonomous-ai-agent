import time
import json
import logging
from typing import List, Optional
from datetime import datetime

from app.models.task import GoalRequest, SubTask, TaskStatus, ExecutionStep, ExecutionResult
from app.models.agent import AgentState
from app.agent.planner import plan_task
from app.agent.tools import default_registry
from app.agent.memory import MemoryManager
from app.agent.llm import LLMClient

logger = logging.getLogger("sazon.executor")


class SazonExecutor:
    """Autonomous agent execution engine for Sazon."""

    def __init__(self, goal_request: GoalRequest):
        self.goal_request = goal_request
        self.memory = MemoryManager()
        self.llm = LLMClient(provider=goal_request.llm_provider)
        self.state = AgentState(
            goal=goal_request.goal,
            context=goal_request.context,
            max_iterations=goal_request.max_iterations
        )

    def run(self) -> ExecutionResult:
        start_time = time.time()
        logger.info(f"Starting Sazon execution for goal: {self.goal_request.goal}")

        # Step 1: Generate Plan
        self.state.subtasks = plan_task(
            goal=self.goal_request.goal,
            context=self.goal_request.context,
            llm_provider=self.goal_request.llm_provider
        )
        self.memory.add_working_memory(
            content=f"Generated {len(self.state.subtasks)} subtasks for goal: {self.goal_request.goal}",
            category="planning"
        )

        # Step 2: Execution Loop
        while not self.state.is_finished and self.state.iteration < self.state.max_iterations:
            self.state.iteration += 1

            # Get next pending subtask
            next_task = self._get_next_subtask()
            if not next_task:
                logger.info("All subtasks processed. Evaluating goal completion...")
                self._evaluate_goal_completion()
                break

            next_task.status = TaskStatus.IN_PROGRESS
            logger.info(f"Iteration {self.state.iteration}: Executing subtask '{next_task.title}'")

            # Execute tool if required
            observation = ""
            if next_task.tool_name:
                tool_input = next_task.tool_input or {}
                observation = default_registry.execute(next_task.tool_name, tool_input)
            else:
                observation = f"Completed step: {next_task.description}"

            next_task.result = observation
            next_task.status = TaskStatus.COMPLETED

            # Record step execution
            step = ExecutionStep(
                step_number=self.state.iteration,
                task_id=next_task.id,
                task_title=next_task.title,
                tool_used=next_task.tool_name,
                tool_input=next_task.tool_input,
                observation=observation,
                status=next_task.status
            )
            self.state.completed_steps.append(step)
            self.memory.add_working_memory(
                content=f"Subtask '{next_task.title}' result: {observation[:200]}",
                category="execution"
            )

        # Check if max iterations reached without finish
        if not self.state.is_finished:
            self.state.is_finished = True
            if not self.state.final_answer:
                self.state.final_answer = self._generate_final_summary()

        elapsed = time.time() - start_time
        return ExecutionResult(
            goal=self.goal_request.goal,
            success=True,
            final_answer=self.state.final_answer or "Goal completed successfully.",
            tasks=self.state.subtasks,
            steps=self.state.completed_steps,
            total_iterations=self.state.iteration,
            execution_time_seconds=round(elapsed, 2)
        )

    def _get_next_subtask(self) -> Optional[SubTask]:
        for task in self.state.subtasks:
            if task.status == TaskStatus.PENDING:
                # Check dependencies
                deps_met = True
                for dep_id in task.dependencies:
                    dep_task = next((t for t in self.state.subtasks if t.id == dep_id), None)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        deps_met = False
                        break
                if deps_met:
                    return task
        return None

    def _evaluate_goal_completion(self):
        context_summary = self.memory.get_context_summary()
        prompt = f"""
Goal: "{self.goal_request.goal}"
Execution Summary:
{context_summary}

Has the goal been completely satisfied? Provide a final comprehensive response for the user.
"""
        response = self.llm.generate(prompt)
        self.state.final_answer = response.strip()
        self.state.is_finished = True

    def _generate_final_summary(self) -> str:
        results = [f"Step {s.step_number} [{s.task_title}]: {s.observation[:150]}" for s in self.state.completed_steps]
        return f"Goal '{self.goal_request.goal}' executed.\nSummary of actions:\n" + "\n".join(results)


def execute_task(goal_input) -> ExecutionResult:
    """Convenience function to run goal through SazonExecutor."""
    if isinstance(goal_input, str):
        req = GoalRequest(goal=goal_input)
    elif isinstance(goal_input, list): # Legacy tuple/list support
        goal_text = "Execute task sequence"
        req = GoalRequest(goal=goal_text)
    else:
        req = goal_input

    executor = SazonExecutor(req)
    return executor.run()