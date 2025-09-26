"""FastAPI surface for launching asynchronous orchestrator runs."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .services import AsyncCallbackManager, AsyncDBConnector, AsyncOrchestrator


STAGES: List[str] = [
    "ingest_docs",
    "planner",
    "emit_tool_specs",
    "dispatch_tools",
    "substitute_vars",
    "synthesize_artifacts",
    "worker_execute_suite",
    "collect_evidence",
    "resolver",
    "postmortem_and_heal",
    "completed",
]


class OrchestrateRequest(BaseModel):
    doc_path: str
    run_id: Optional[str] = None


class OrchestrateResponse(BaseModel):
    run_id: str
    coverage: float
    execution_pass_rate: float
    flake_rate: float


app = FastAPI(title="Agent Test Orchestrator", version="0.2.0")
_callbacks = AsyncCallbackManager()
_db = AsyncDBConnector()
_orchestrator = AsyncOrchestrator(callbacks=_callbacks, db=_db)
_stage_history: Dict[str, List[str]] = {}


async def _register_stage_logging(run_id: str) -> None:
    await _callbacks.clear()
    for stage in STAGES:
        async def _logger(state, stage_name=stage, run_key=run_id):  # type: ignore[override]
            history = _stage_history.setdefault(run_key, [])
            history.append(stage_name)

        await _callbacks.register(stage, _logger)


@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    run_id = request.run_id or request.doc_path
    await _register_stage_logging(run_id)
    outcome = await _orchestrator.run(request.doc_path, run_id=run_id)
    metrics = outcome.metrics
    return OrchestrateResponse(
        run_id=run_id,
        coverage=outcome.evidence_bundle.report.coverage,
        execution_pass_rate=metrics.execution_pass_rate,
        flake_rate=metrics.flake_rate,
    )


@app.get("/outcomes")
async def list_runs() -> Dict[str, str]:
    return await _db.list_keys()


@app.get("/outcomes/{run_id}")
async def get_outcome(run_id: str) -> Dict[str, object]:
    outcome = await _db.load_outcome(run_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="run_id not found")
    return outcome.to_dict()


@app.get("/outcomes/{run_id}/stages")
async def get_stage_history(run_id: str) -> List[str]:
    history = _stage_history.get(run_id)
    if history is None:
        raise HTTPException(status_code=404, detail="stage history not found")
    return history
