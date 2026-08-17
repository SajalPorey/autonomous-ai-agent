import json
import logging
from typing import List, Optional
from app.models.task import SubTask, TaskStatus
from app.agent.llm import LLMClient
from app.agent.tools import default_registry

logger = logging.getLogger("sazon.planner")


def plan_task(goal: str, context: Optional[str] = None, llm_provider: Optional[str] = None) -> List[SubTask]:
    """Decomposes a high-level user goal into ordered, structured subtasks."""
    llm = LLMClient(provider=llm_provider)
    available_tools = default_registry.list_tools()

    system_instruction = (
        "You are Sazon, an advanced Autonomous AI Agent Planner. "
        "Your job is to break down user goals into clean, logical subtasks. "
        "Each subtask should specify a priority (1 is highest), description, "
        "and recommended tool if applicable. Return valid JSON only."
    )

    prompt = f"""
Goal: "{goal}"
Context: "{context or 'None'}"

Available Tools:
{json.dumps(available_tools, indent=2)}

Output Schema Requirement (JSON object with 'subtasks' list):
{{
  "subtasks": [
    {{
      "id": "task_1",
      "title": "Short title",
      "description": "Detailed step description",
      "priority": 1,
      "tool_name": "tool_name_or_null",
      "tool_input": {{ "arg_name": "arg_value" }},
      "dependencies": []
    }}
  ]
}}
"""

    response_text = llm.generate(prompt, system_instruction=system_instruction, json_mode=True)

    subtasks: List[SubTask] = []
    try:
        # Extract JSON from potential code blocks in response
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        raw_tasks = data.get("subtasks", [])

        for idx, task_data in enumerate(raw_tasks, start=1):
            subtask = SubTask(
                id=task_data.get("id", f"task_{idx}"),
                title=task_data.get("title", f"Subtask {idx}"),
                description=task_data.get("description", ""),
                priority=task_data.get("priority", idx),
                status=TaskStatus.PENDING,
                tool_name=task_data.get("tool_name"),
                tool_input=task_data.get("tool_input"),
                dependencies=task_data.get("dependencies", [])
            )
            subtasks.append(subtask)

    except Exception as e:
        logger.warning(f"Failed to parse LLM planning JSON output: {e}. Using rule-based fallback plan.")
        # Rule-based fallback planning
        subtasks = [
            SubTask(
                id="task_1",
                title=f"Inspect system and gather facts for '{goal[:30]}'",
                description="Gather environment details and inspect initial scope.",
                priority=1,
                tool_name="system_info",
                tool_input={},
                status=TaskStatus.PENDING
            ),
            SubTask(
                id="task_2",
                title=f"Execute primary action for '{goal[:30]}'",
                description="Process and generate solution for goal.",
                priority=2,
                tool_name="file_write",
                tool_input={"filepath": "sazon_output.txt", "content": f"Sazon Execution Output for: {goal}"},
                status=TaskStatus.PENDING
            ),
            SubTask(
                id="task_3",
                title="Synthesize and finalize results",
                description="Verify outputs and build final answer.",
                priority=3,
                tool_name=None,
                tool_input=None,
                status=TaskStatus.PENDING
            )
        ]

    # Sort subtasks by priority
    subtasks.sort(key=lambda t: t.priority)
    return subtasks
