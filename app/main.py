from fastapi import FastAPI
from app.agent.planner import plan_task
from app.agent.executor import execute_task

app = FastAPI(title="Autonomous AI Agent")

@app.get("/")
def root():
    return {"status": "Agent running successfully"}

@app.post("/run")
def run_agent(goal: str):
    tasks = plan_task(goal)
    results = execute_task(tasks)
    return {
        "goal": goal,
        "execution_result": results
    }
