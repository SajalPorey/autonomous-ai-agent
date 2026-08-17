import os
import pytest
from app.models.task import GoalRequest, TaskStatus
from app.agent.tools import ToolRegistry, default_registry
from app.agent.memory import MemoryManager
from app.agent.planner import plan_task
from app.agent.executor import SazonExecutor, execute_task


def test_tool_registry():
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert len(tools) >= 5

    # Test file_write and file_read
    write_res = registry.execute("file_write", {"filepath": "test_tmp.txt", "content": "Hello Sazon"})
    assert "Successfully wrote" in write_res

    read_res = registry.execute("file_read", {"filepath": "test_tmp.txt"})
    assert read_res == "Hello Sazon"

    # Test create_folder and file_search
    folder_res = registry.execute("create_folder", {"folder_path": "test_dir"})
    assert "created or verified" in folder_res

    search_res = registry.execute("file_search", {"pattern": "test_tmp.txt", "directory": "."})
    assert "test_tmp.txt" in search_res

    # Test system_status
    sys_res = registry.execute("system_status", {})
    assert "platform" in sys_res

    # Cleanup
    if os.path.exists("test_tmp.txt"):
        os.remove("test_tmp.txt")
    if os.path.exists("test_dir"):
        os.rmdir("test_dir")


def test_memory_manager():
    mem = MemoryManager(memory_file=".test_memory.json")
    mem.add_working_memory("Test observation", category="test")
    assert len(mem.short_term_memory) == 1

    mem.save_persistent("key1", "val1")
    assert mem.get_persistent("key1") == "val1"

    if os.path.exists(".test_memory.json"):
        os.remove(".test_memory.json")


def test_planner():
    subtasks = plan_task("Test goal for laptop assistant planning")
    assert len(subtasks) > 0
    assert subtasks[0].status == TaskStatus.PENDING


def test_executor():
    req = GoalRequest(goal="Create a test report file", max_iterations=3)
    executor = SazonExecutor(req)
    result = executor.run()

    assert result.goal == req.goal
    assert result.success is True
    assert len(result.tasks) > 0
    assert len(result.steps) > 0
