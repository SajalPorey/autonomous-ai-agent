from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


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
