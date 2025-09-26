# Agent-Test-Orchestrator

An open-source proof-of-concept for coordinating LLM-based testing agents. The project demonstrates an asynchronous ReWOO + MCP orchestrator that converts natural language product documentation into runnable, self-healing test suites for web and mobile.

## Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) for managing virtual environments and installing dependencies

## Installation
```bash
# Create and activate an isolated environment managed by uv
uv venv .venv
source .venv/bin/activate

# Install the project and its runtime dependencies in editable mode
uv pip install -e .
```

## Command-Line Orchestrator
Run the CLI against one of the example documentation bundles to generate a test suite:
```bash
python -m orchestrator --doc examples/sample_docs/web_user_stories.md
```
Generated artifacts, run metrics, and healing proposals are printed to the console and persisted under `artifacts/` and `data/`.

## FastAPI Service
The HTTP API is defined in `src/orchestrator/api.py` via the `create_app` factory. Launch it with Uvicorn after activating the environment:
```bash
uvicorn orchestrator.api:app --reload
```

### Endpoints
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/start` | Begin orchestrating a new run for the supplied documentation bundle. Optional `run_id` avoids collisions. |
| `GET` | `/check/{run_id}` | Inspect the lifecycle state, observed stages, and outcome (if completed) for a specific run. |
| `POST` | `/cancel/{run_id}` | Request cancellation for an active run; returns the latest known state. |

### Request & Response Models
- `POST /start`
  ```json
  {
    "doc_path": "examples/sample_docs/web_user_stories.md",
    "run_id": "web-suite-001",
    "callback_url": "https://example.com/hooks/tests"
  }
  ```
  - Returns `202 Accepted` with the generated `run_id` plus an initial lifecycle snapshot.
- `GET /check/{run_id}`
  - Returns the run metadata including `status`, completed `stages`, any serialized `result`, and error details if applicable.
- `POST /cancel/{run_id}`
  - Moves the run to a terminal state when possible and reports whether the run had already finished or was cancelled.

### Callback Webhooks
Provide a `callback_url` when starting a run to receive asynchronous completion updates. The orchestrator delivers a JSON payload:
```json
{
  "run_id": "web-suite-001",
  "status": "completed",
  "result": {"summary": "..."},
  "error": null
}
```
If delivery fails, the response body includes `callback_error` so you can investigate.

## Development & Testing
Install development dependencies and execute the test suite:
```bash
uv pip install -e .[dev]
pytest
```

## License
[MIT](LICENSE)
