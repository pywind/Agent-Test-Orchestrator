# Troubleshooting Guide

## Planner Output Missing Sub-Questions
- Confirm the input documentation includes bullet lists describing user stories or requirements.
- Review the planner configuration (`PlannerConfig`) to ensure `min_sub_questions` is ≥8.
- Inspect LangGraph planner node logs for exceptions and re-run with `LANGGRAPH_DEBUG=1`.

## Tool Execution Deadlocks
- Validate that ToolSpecs include accurate dependencies; cycles cause the dispatcher to halt.
- Ensure MCP tool stubs are registered in `_TOOL_IMPLEMENTATIONS` within `execution.py`.
- Increase dispatcher worker threads via `ExecutionDispatcher(max_workers=8)` for large plans.

## Missing Evidence Artifacts
- Verify artifact store path permissions; the stub writes to `artifacts/` relative to the project root.
- Confirm media toggles in the selected environment profile enable screenshots/video capture.
- Re-run the suite with `--profile web-local` to capture full evidence for debugging.

## Locator Drift Not Detected
- Ensure failing tests propagate selector-related error messages; heuristics look for `"selector"` keyword.
- Augment `detect_locator_drift` with additional heuristics from production telemetry as needed.
