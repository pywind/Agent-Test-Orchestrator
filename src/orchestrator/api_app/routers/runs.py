"""Routers exposing the orchestration lifecycle endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies.run_manager import get_run_manager
from ..models.run import (
    CancelRunResponse,
    RunMetadata,
    RunStatusResponse,
    StartRunRequest,
    StartRunResponse,
)
from ..services.run_manager import RunManager, RunRecord, RunStatus

router = APIRouter(tags=["runs"])


def _build_metadata(record: RunRecord) -> RunMetadata:
    return RunMetadata.model_validate(
        {
            "run_id": record.run_id,
            "doc_path": record.doc_path,
            "status": record.status,
            "stages": list(record.stages),
            "result": record.result,
            "error": record.error,
            "callback_url": record.callback_url,
            "callback_error": record.callback_error,
        }
    )


@router.post("/start", response_model=StartRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    payload: StartRunRequest,
    run_manager: RunManager = Depends(get_run_manager),
) -> StartRunResponse:
    try:
        record = await run_manager.start_run(
            payload.doc_path,
            run_id=payload.run_id,
            callback_url=str(payload.callback_url) if payload.callback_url else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    metadata = _build_metadata(record)
    return StartRunResponse(**metadata.model_dump(), message="Run started")


@router.get("/check/{run_id}", response_model=RunStatusResponse)
async def check_run(run_id: str, run_manager: RunManager = Depends(get_run_manager)) -> RunStatusResponse:
    try:
        record = await run_manager.check_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    metadata = _build_metadata(record)
    return RunStatusResponse(**metadata.model_dump())


@router.post("/cancel/{run_id}", response_model=CancelRunResponse)
async def cancel_run(run_id: str, run_manager: RunManager = Depends(get_run_manager)) -> CancelRunResponse:
    try:
        record = await run_manager.cancel_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    metadata = _build_metadata(record)
    message = (
        "Run already finished"
        if record.status in {RunStatus.COMPLETED, RunStatus.FAILED}
        else "Run cancelled"
    )
    return CancelRunResponse(**metadata.model_dump(), message=message)
