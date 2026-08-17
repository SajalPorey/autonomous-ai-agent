from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.models.task import SubTask, ExecutionStep


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
