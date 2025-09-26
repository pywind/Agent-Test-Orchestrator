# Orchestrator Runbook

## Pre-Run Checklist
1. Select environment profile (`web-local`, `web-ci`, `mobile-emu`, or `mobile-device`).
2. Ensure MCP servers for filesystem, Playwright, Appium, and artifact store are reachable.
3. Confirm documentation inputs are available in the repository under `examples/sample_docs/` or configured path.

## Execution Steps
1. Install dependencies: `pip install -e .`.
2. Run the orchestrator with the desired Doc Pack:
   ```bash
   python -m orchestrator --doc examples/sample_docs/web_user_stories.md --profile web-local
   ```
3. Monitor LangGraph checkpoints after planner, artifact synthesis, and suite execution.
4. Review generated artifacts in the console output and persisted evidence under `artifacts/`.

## Post-Run Activities
1. Inspect the run report summary for pass/fail and coverage metrics.
2. Review heal proposals and approve selector fixes as needed.
3. File issues for persistent failures or missing requirements.
4. Persist validated selectors into the learning store (`data/learning_store.json`).
