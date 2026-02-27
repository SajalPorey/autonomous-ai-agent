import heapq

def plan_task(goal: str):
    task_queue = []

    subtasks = [
        (2, f"Research about {goal}"),
        (1, f"Design execution plan for {goal}"),
        (3, f"Finalize and review {goal}")
    ]

    for priority, task in subtasks:
        heapq.heappush(task_queue, (priority, task))

    return task_queue
