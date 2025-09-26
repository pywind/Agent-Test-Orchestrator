"""Pydantic models for the FastAPI surface."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field

from ..schema import RunStatus


class StartRunRequest(BaseModel):
    doc_path: str = Field(..., description="Path to the documentation bundle consumed by the orchestrator")
    run_id: Optional[str] = Field(None, description="Optional id to associate with the run")
    callback_url: Optional[AnyHttpUrl] = Field(
        None,
        description="If provided, the orchestrator will POST the outcome to this URL when finished",
    )


class RunMetadata(BaseModel):
    run_id: str
    doc_path: str
    status: RunStatus
    stages: List[str] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    callback_url: Optional[AnyHttpUrl] = None
    callback_error: Optional[str] = None


class StartRunResponse(RunMetadata):
    message: str = Field(default="Run started")


class RunStatusResponse(RunMetadata):
    pass


class CancelRunResponse(RunMetadata):
    message: str = Field(default="Run cancelled")
