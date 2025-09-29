# Agent Test Orchestrator Modernization Plan

## Goals
- Remove vestigial LangGraph stub implementation and rely on the new service-oriented workflow.
- Introduce asynchronous orchestration stages backed by Celery tasks.
- Provide FastAPI surface area for launching orchestration runs and retrieving outcomes.
- Persist run results through an asynchronous DB connector abstraction.
- Support callback-driven extensibility so additional behaviors can be attached to stage completions.

## Architecture Overview
1. **Service Layer**
   - `AsyncOrchestrator` coordinates the ordered execution of Celery tasks for each pipeline stage.
   - `AsyncCallbackManager` offers registration and emission of async callbacks per stage, enabling hook points for analytics, notifications, or persistence extensions.
   - `AsyncDBConnector` currently stores outcomes in-memory but mimics async persistence semantics so it can be swapped for a durable database implementation.
2. **Task Queue**
   - Each stage from ingestion through postmortem is implemented as an individual Celery task in `services/task_queue.py`.
   - Celery runs in eager mode for the test environment, ensuring synchronous semantics while retaining production-ready entry points for distributed workers.
3. **FastAPI Application**
   - `orchestrator/api.py` exposes `/orchestrate` to trigger runs, `/outcomes` and `/outcomes/{run_id}` to inspect persisted results, and `/outcomes/{run_id}/stages` to inspect the callback-driven stage history.
   - Stage logging is implemented as an async callback registered per invocation and backed by `_stage_history`.
4. **Testing & Compatibility**
   - `run_orchestrator` now wraps the async workflow with `asyncio.run`, preserving compatibility with existing synchronous tests.
   - The orchestration logic still reuses the rich state management defined in `utils/nodes.py`.

## Next Steps
- Replace the in-memory DB connector with a PostgreSQL or Redis implementation for production deployments.
- Integrate real Celery brokers/backends and disable eager mode outside of tests.
- Expand the FastAPI layer with authentication and streaming updates for long-running stages.
- Add observability hooks (metrics, tracing) via the callback manager.
