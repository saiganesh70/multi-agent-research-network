"""FastAPI service exposing the Multi-Agent Research Network.

Flow:
1. POST /research           -> kicks off the crew, returns a run_id, status="pending_approval"
                               once a draft report is generated (human-in-the-loop gate).
2. GET  /research/{run_id}  -> poll for status / draft report.
3. POST /research/{run_id}/approve -> approve or reject the draft.
                                        Approved reports are marked "completed" and persisted.
"""

import logging
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.crew import run_with_fallback
from app.models import ApprovalDecision, PipelineRunStatus, ResearchRequest

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Multi-Agent Research Network",
    description="CrewAI-powered market research automation pipeline (Researcher -> Analyst -> Writer).",
    version="1.0.0",
)

# In-memory store for demo purposes. Swap for Redis/DB in production.
RUNS: dict[str, PipelineRunStatus] = {}


def _execute_pipeline(run_id: str, req: ResearchRequest) -> None:
    RUNS[run_id].status = "running"
    report = run_with_fallback(
        company_name=req.company_name,
        industry=req.industry,
        focus_areas=req.focus_areas,
        pdf_path=req.pdf_path,
    )
    RUNS[run_id].report_markdown = report
    # Draft is ready — wait for a human to approve before treating it as final.
    RUNS[run_id].status = "pending_approval"


@app.post("/research", response_model=PipelineRunStatus)
def start_research(req: ResearchRequest, background_tasks: BackgroundTasks) -> PipelineRunStatus:
    run_id = str(uuid.uuid4())
    status = PipelineRunStatus(
        run_id=run_id,
        status="running",
        created_at=datetime.now(timezone.utc),
        company_name=req.company_name,
    )
    RUNS[run_id] = status
    background_tasks.add_task(_execute_pipeline, run_id, req)
    return status


@app.get("/research/{run_id}", response_model=PipelineRunStatus)
def get_research_status(run_id: str) -> PipelineRunStatus:
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run_id not found")
    return RUNS[run_id]


@app.post("/research/{run_id}/approve", response_model=PipelineRunStatus)
def approve_research(run_id: str, decision: ApprovalDecision) -> PipelineRunStatus:
    """Human-in-the-loop gate: a reviewer approves or rejects the draft report."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run_id not found")

    run = RUNS[run_id]
    if run.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Run is in status '{run.status}', not awaiting approval.",
        )

    run.status = "completed" if decision.approve else "rejected"
    if decision.reviewer_notes:
        run.report_markdown = (run.report_markdown or "") + f"\n\n---\n**Reviewer notes:** {decision.reviewer_notes}"
    return run


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
