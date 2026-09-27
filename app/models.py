"""Pydantic schemas for the Multi-Agent Research Network API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    company_name: str = Field(..., description="Company or competitor to research")
    industry: Optional[str] = Field(None, description="Industry context to focus the research")
    focus_areas: Optional[list[str]] = Field(
        default=None,
        description="Specific angles to investigate, e.g. ['pricing', 'recent funding', 'product launches']",
    )
    pdf_path: Optional[str] = Field(
        default=None, description="Optional path to a local PDF (e.g. an existing competitor report) to include as context"
    )


class PipelineRunStatus(BaseModel):
    run_id: str
    status: str  # "pending_approval" | "running" | "completed" | "failed" | "rejected"
    created_at: datetime
    company_name: str
    report_markdown: Optional[str] = None
    error: Optional[str] = None


class ApprovalDecision(BaseModel):
    approve: bool
    reviewer_notes: Optional[str] = None
