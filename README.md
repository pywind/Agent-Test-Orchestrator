# Agent-Test-Orchestrator

An open-source proof-of-concept for coordinating LLM-based testing agents. This repository now includes a detailed build plan for an asynchronous ReWOO + MCP orchestrator that can translate product documentation into runnable test suites across web and mobile targets.

## Getting Started
- Review the [POC orchestration plan](docs/poc_plan.md) for architecture, scope, work breakdown, and acceptance criteria.
- Install dependencies with [uv](https://github.com/astral-sh/uv) and run the orchestrator CLI:
  ```bash
  uv pip install -e .
  python -m orchestrator --doc examples/sample_docs/web_user_stories.md
  ```
- Generated artifacts, run metrics, and healing proposals are printed to the console and persisted under `artifacts/` and `data/`.
- The FastAPI surface lives in `orchestrator/api.py`; launch it with Uvicorn to orchestrate runs over HTTP while Celery coordinates stage execution. The service exposes `/start`, `/check/{run_id}`, and `/cancel/{run_id}` endpoints and can optionally deliver results via callback webhooks for downstream systems.

## Status
The repository now includes an asynchronous Celery-powered ReWOO orchestrator with MCP tool stubs, configuration profiles, and documentation to validate the proof of concept end-to-end.

## License
[MIT](LICENSE)
