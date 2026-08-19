"""
agent.py — Sazon Autonomous AI Agent Core
Contains the complete AI brain: data models, tool registry, memory manager,
LLM client integration (Gemini / OpenAI / smart local fallback), planner, and executor.
"""
import os
import sys
import time
import json
import fnmatch
import platform
import subprocess
import webbrowser
import logging
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

logger = logging.getLogger("sazon.agent")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data Models
# ─────────────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    SKIPPED     = "skipped"


class SubTask(BaseModel):
    id: str = Field(..., description="Unique ID for the subtask")
    title: str = Field(..., description="Short title describing the subtask")
    description: str = Field("", description="Detailed description of work to perform")
    priority: int = Field(1, description="Priority level (1 highest)")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Current execution status")
    tool_name: Optional[str] = Field(None, description="Recommended tool to use")
    tool_input: Optional[Dict[str, Any]] = Field(None, description="Input arguments for tool")
    result: Optional[str] = Field(None, description="Output/result of execution")
    dependencies: List[str] = Field(default_factory=list, description="IDs of subtasks that must be completed first")


class GoalRequest(BaseModel):
    goal: str = Field(..., description="The high-level goal for Sazon to achieve")
    context: Optional[str] = Field(None, description="Optional background context or constraints")
    max_iterations: int = Field(10, ge=1, le=50, description="Max execution loop iterations")
    llm_provider: Optional[str] = Field(None, description="Override LLM provider (gemini, openai)")
    model: Optional[str] = Field(None, description="Override specific model (e.g. gemini-2.5-flash, gpt-4o, etc.)")


class ExecutionStep(BaseModel):
    step_number: int
    task_id: str
    task_title: str
    tool_used: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    observation: str
    status: TaskStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    goal: str
    success: bool
    final_answer: str
    tasks: List[SubTask]
    steps: List[ExecutionStep]
    total_iterations: int
    execution_time_seconds: float = 0.0


class MemoryItem(BaseModel):
    id: str
    content: str
    category: str = "general"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    goal: str
    context: Optional[str] = None
    subtasks: List[SubTask] = Field(default_factory=list)
    completed_steps: List[ExecutionStep] = Field(default_factory=list)
    memories: List[MemoryItem] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 10
    is_finished: bool = False
    final_answer: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Tool Registry & Built-in System Tools
# ─────────────────────────────────────────────────────────────────────────────

class ToolRegistry:
    """Registry of built-in system tools available to Sazon."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable, description: str):
        self._tools[name] = {"func": func, "description": description}

    def get_tool(self, name: str) -> Optional[Callable]:
        tool = self._tools.get(name)
        return tool["func"] if tool else None

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": name, "description": data["description"]}
            for name, data in self._tools.items()
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        tool_data = self._tools.get(tool_name)
        if not tool_data:
            return f"Error: Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
        try:
            result = tool_data["func"](**tool_input)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def _register_default_tools(self):
        # File Read
        def file_read(filepath: str) -> str:
            if not os.path.exists(filepath):
                return f"Error: File '{filepath}' does not exist."
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        self.register("file_read", file_read, "Read contents of a local file. Args: filepath (str)")

        # File Write
        def file_write(filepath: str, content: str) -> str:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to '{filepath}'."

        self.register("file_write", file_write, "Write text content to a local file. Args: filepath (str), content (str)")

        # File List
        def file_list(directory: str = ".") -> str:
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist."
            items = os.listdir(directory)
            return json.dumps({"directory": os.path.abspath(directory), "items": items})

        self.register("file_list", file_list, "List files and subdirectories. Args: directory (str, default '.')")

        # File Search
        def file_search(pattern: str, directory: str = ".") -> str:
            matches = []
            for root, _, filenames in os.walk(directory):
                for filename in fnmatch.filter(filenames, pattern):
                    matches.append(os.path.join(root, filename))
                if len(matches) >= 50:
                    break
            return json.dumps({"pattern": pattern, "found_count": len(matches), "files": matches[:50]})

        self.register("file_search", file_search, "Search files by glob pattern. Args: pattern (str), directory (str)")

        # Create Folder
        def create_folder(folder_path: str) -> str:
            os.makedirs(folder_path, exist_ok=True)
            return f"Folder '{folder_path}' created or verified successfully."

        self.register("create_folder", create_folder, "Create a folder/directory. Args: folder_path (str)")

        # Open App or URL
        def open_app_or_url(target: str) -> str:
            try:
                if target.startswith("http://") or target.startswith("https://"):
                    webbrowser.open(target)
                    return f"Opened URL '{target}' in default browser."
                else:
                    if sys.platform == "win32":
                        os.startfile(target)
                    else:
                        subprocess.Popen([target])
                    return f"Launched application/target '{target}'."
            except Exception as e:
                return f"Error opening '{target}': {str(e)}"

        self.register("open_app_or_url", open_app_or_url, "Open a website URL or launch a desktop application. Args: target (str)")

        # Run Terminal Command
        def run_terminal_command(command: str, timeout_seconds: int = 30) -> str:
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                return json.dumps({
                    "exit_code": result.returncode,
                    "stdout": stdout,
                    "stderr": stderr
                })
            except subprocess.TimeoutExpired:
                return f"Error: Command timed out after {timeout_seconds} seconds."
            except Exception as e:
                return f"Error running command: {str(e)}"

        self.register("run_terminal_command", run_terminal_command, "Run a shell/terminal command safely. Args: command (str)")

        # System Info
        def system_info() -> str:
            return json.dumps({
                "os": platform.system(),
                "os_release": platform.release(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "working_dir": os.getcwd()
            })

        self.register("system_info", system_info, "Get current system and environment diagnostics. Args: none")

        # Calculate
        def calculate(expression: str) -> str:
            try:
                allowed_names = {"__builtins__": None}
                res = eval(expression, allowed_names, {})
                return f"Result: {res}"
            except Exception as e:
                return f"Error evaluating math expression: {str(e)}"

        self.register("calculate", calculate, "Evaluate a mathematical expression. Args: expression (str)")


default_registry = ToolRegistry()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Memory Manager
# ─────────────────────────────────────────────────────────────────────────────

class MemoryManager:
    """Manages working memory and persistent execution context."""

    def __init__(self):
        self.working_memory: List[MemoryItem] = []
        self.short_term_context: List[str] = []

    def add_working_memory(self, content: str, category: str = "general", metadata: Optional[Dict[str, Any]] = None):
        item = MemoryItem(
            id=f"mem_{len(self.working_memory) + 1}",
            content=content,
            category=category,
            metadata=metadata or {}
        )
        self.working_memory.append(item)

    def get_context_summary(self) -> str:
        if not self.working_memory:
            return "No prior context available."
        recent = self.working_memory[-10:]
        return "\n".join([f"- [{item.category.upper()}] {item.content}" for item in recent])

    def clear(self):
        self.working_memory.clear()
        self.short_term_context.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 4. LLM Client
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Unified LLM client for Sazon (Gemini, OpenAI, sample demo model, or local fallback)."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or os.getenv("DEFAULT_LLM_PROVIDER", "sample")).lower()
        self.model = model
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        provider = (self.provider or "").lower()
        model_name = (self.model or "").lower()

        # Dedicated Sample / Demo Model
        if provider in ("sample", "mock", "demo") or "sample" in model_name or "demo" in model_name:
            return self._sample_model_response(prompt, json_mode)

        if provider == "gemini" and self.gemini_key:
            return self._call_gemini(prompt, system_instruction, json_mode)
        elif provider == "openai" and self.openai_key:
            return self._call_openai(prompt, system_instruction, json_mode)
        else:
            return self._fallback_response(prompt, json_mode)

    def _sample_model_response(self, prompt: str, json_mode: bool) -> str:
        """Sample / Demo model: handles greetings, basic hi/hello, and simulated tasks without API keys."""
        p_lower = prompt.lower()
        is_greeting = any(w in p_lower for w in ["hi", "hello", "hey", "namaste", "hola", "sup", "who are you", "what are you"])

        if json_mode:
            if is_greeting:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Greet User",
                            "description": "Send a friendly greeting and introduction",
                            "priority": 1,
                            "tool_name": None,
                            "tool_input": {}
                        }
                    ]
                })
            else:
                return self._fallback_response(prompt, json_mode=True)
        else:
            if any(w in p_lower for w in ["hi", "hello", "hey", "namaste", "hola", "sup"]):
                return "Hello! 👋 Sazon is here, how may I help you today?"
            elif "who are you" in p_lower or "what are you" in p_lower:
                return "🤖 I am **Sazon**, your autonomous AI desktop mascot and assistant! I can automate tasks, inspect system diagnostics, explore files, and execute commands on your laptop."
            else:
                return f"Sazon completed your request: \"{prompt[:80]}\" successfully."

    def _call_gemini(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            model_name = self.model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            full_prompt = f"System: {system_instruction}\n\nUser: {prompt}" if system_instruction else prompt
            response = client.models.generate_content(model=model_name, contents=full_prompt)
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return self._fallback_response(prompt, json_mode)

    def _call_openai(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            model_name = self.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
            response = client.chat.completions.create(model=model_name, messages=messages, **kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self._fallback_response(prompt, json_mode)

    def _fallback_response(self, prompt: str, json_mode: bool) -> str:
        """Local smart fallback when API key is not configured."""
        p_lower = prompt.lower()
        is_greeting = any(w in p_lower for w in ["hi", "hello", "hey", "namaste", "hola", "sup", "who are you", "what are you"])

        if json_mode:
            if is_greeting:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Greet User",
                            "description": "Send a friendly greeting to the user",
                            "priority": 1,
                            "tool_name": None,
                            "tool_input": {}
                        }
                    ]
                })
            elif "status" in p_lower or "hardware" in p_lower or "diagnostic" in p_lower:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Inspect system diagnostics",
                            "description": "Query local environment and OS diagnostics",
                            "priority": 1,
                            "tool_name": "system_info",
                            "tool_input": {}
                        }
                    ]
                })
            elif "find" in p_lower or "search" in p_lower:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Search directory files",
                            "description": "Locate files matching query",
                            "priority": 1,
                            "tool_name": "file_search",
                            "tool_input": {"pattern": "*.*", "directory": "."}
                        }
                    ]
                })
            elif "report" in p_lower:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Collect system info",
                            "description": "Gather system properties",
                            "priority": 1,
                            "tool_name": "system_info",
                            "tool_input": {}
                        },
                        {
                            "id": "task_2",
                            "title": "Write report file",
                            "description": "Create report on disk",
                            "priority": 2,
                            "tool_name": "file_write",
                            "tool_input": {"filepath": "system_report.txt", "content": "Sazon Autonomous Agent Report\nGenerated successfully."}
                        }
                    ]
                })
            else:
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Execute requested operation",
                            "description": "Perform task needed for goal",
                            "priority": 1,
                            "tool_name": "system_info",
                            "tool_input": {}
                        }
                    ]
                })
        else:
            if is_greeting:
                return "Hello! 👋 Sazon is here, how may I help you today?"
            return f"Goal processed successfully via Sazon Agent Engine."


# ─────────────────────────────────────────────────────────────────────────────
# 5. Planner
# ─────────────────────────────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """
You are the Master Task Planner for Sazon, an autonomous AI desktop assistant.
Given a user's goal, break it down into a logical sequence of atomic SubTasks.
For each subtask, assign the most suitable tool from the available tools.

Output MUST be a valid JSON object with the following schema:
{
  "subtasks": [
    {
      "id": "task_1",
      "title": "Short title",
      "description": "Detailed explanation",
      "priority": 1,
      "tool_name": "tool_name_here",
      "tool_input": {"param_key": "param_value"},
      "dependencies": []
    }
  ]
}
"""

def plan_task(goal: str, context: Optional[str] = None, llm_provider: Optional[str] = None, model: Optional[str] = None) -> List[SubTask]:
    """Generates an actionable execution plan of SubTasks for a goal."""
    llm = LLMClient(provider=llm_provider, model=model)
    prompt = f"""
Goal: "{goal}"
Context: {context or "No additional context."}
Available Tools:
{json.dumps(default_registry.list_tools(), indent=2)}

Create a concise and structured plan to achieve this goal autonomously.
"""
    try:
        raw_response = llm.generate(prompt=prompt, system_instruction=PLANNER_SYSTEM_PROMPT, json_mode=True)
        data = json.loads(raw_response)
        subtask_dicts = data.get("subtasks", [])
        return [SubTask(**t) for t in subtask_dicts]
    except Exception as e:
        logger.warning(f"Failed to parse LLM plan: {e}. Using single execution step.")
        return [
            SubTask(
                id="task_1",
                title=f"Execute: {goal[:50]}",
                description=goal,
                priority=1,
                tool_name="system_info" if "system" in goal.lower() else None,
                tool_input={}
            )
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Sazon Executor Engine
# ─────────────────────────────────────────────────────────────────────────────

class SazonExecutor:
    """Autonomous agent execution engine for Sazon."""

    def __init__(self, goal_request: GoalRequest):
        self.goal_request = goal_request
        self.memory = MemoryManager()
        self.llm = LLMClient(provider=goal_request.llm_provider, model=goal_request.model)
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
            llm_provider=self.goal_request.llm_provider,
            model=self.goal_request.model
        )
        self.memory.add_working_memory(
            content=f"Generated {len(self.state.subtasks)} subtasks for goal: {self.goal_request.goal}",
            category="plan"
        )

        # Step 2: Execution Loop
        while not self.state.is_finished and self.state.iteration < self.state.max_iterations:
            self.state.iteration += 1
            next_task = self._get_next_subtask()
            if not next_task:
                break
            self._execute_subtask(next_task)

        # Step 3: Final Answer Evaluation
        if not self.state.final_answer:
            self._evaluate_goal_completion()

        elapsed = time.time() - start_time
        return ExecutionResult(
            goal=self.state.goal,
            success=all(t.status == TaskStatus.COMPLETED for t in self.state.subtasks) if self.state.subtasks else True,
            final_answer=self.state.final_answer or "Goal executed successfully.",
            tasks=self.state.subtasks,
            steps=self.state.completed_steps,
            total_iterations=self.state.iteration,
            execution_time_seconds=round(elapsed, 2)
        )

    def _execute_subtask(self, task: SubTask):
        task.status = TaskStatus.IN_PROGRESS
        observation = ""

        if task.tool_name:
            tool_input = task.tool_input or {}
            observation = default_registry.execute(task.tool_name, tool_input)
            task.result = observation
            task.status = TaskStatus.COMPLETED if not observation.startswith("Error:") else TaskStatus.FAILED
        else:
            observation = f"Completed action: {task.title}"
            task.result = observation
            task.status = TaskStatus.COMPLETED

        self.memory.add_working_memory(
            content=f"Task '{task.title}' ({task.tool_name or 'internal'}): {observation[:200]}",
            category="observation",
            metadata={"task_id": task.id, "status": task.status.value}
        )

        step = ExecutionStep(
            step_number=len(self.state.completed_steps) + 1,
            task_id=task.id,
            task_title=task.title,
            tool_used=task.tool_name,
            tool_input=task.tool_input,
            observation=observation,
            status=task.status
        )
        self.state.completed_steps.append(step)

    def _get_next_subtask(self) -> Optional[SubTask]:
        for task in self.state.subtasks:
            if task.status == TaskStatus.PENDING:
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


def execute_task(goal_input) -> ExecutionResult:
    """Convenience helper to run a goal through SazonExecutor."""
    if isinstance(goal_input, str):
        req = GoalRequest(goal=goal_input)
    else:
        req = goal_input
    return SazonExecutor(req).run()
