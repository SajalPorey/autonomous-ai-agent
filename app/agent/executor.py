import heapq

def execute_task(task_queue):
    results = []

    while task_queue:
        priority, task = heapq.heappop(task_queue)
        results.append(f"Executed (priority {priority}): {task}")

    return results