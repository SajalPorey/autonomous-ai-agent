from fastapi import FastAPI, HTTPException, BackgroundTasks
from app.models.task import GoalRequest, ExecutionResult
from app.agent.executor import SazonExecutor
from app.agent.tools import default_registry

app = FastAPI(
    title="Sazon Autonomous AI Agent API",
    description="REST API for Sazon - Autonomous AI Agent Engine",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "agent": "Sazon",
        "status": "online",
        "description": "Autonomous AI Agent Engine initialized and ready to execute goals."
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "sazon-agent"}

@app.get("/tools")
def list_tools():
    """Returns list of active tools available to Sazon."""
    return {"tools": default_registry.list_tools()}

@app.post("/run", response_model=ExecutionResult)
def run_agent(request: GoalRequest):
    """Executes a goal autonomously using Sazon Agent."""
    try:
        executor = SazonExecutor(request)
        result = executor.run()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sazon execution failed: {str(e)}")
