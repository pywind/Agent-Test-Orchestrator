# POC LLM Orchestrator for Test Automation

## Goal & Scope
- **Objective:** Build a proof-of-concept orchestrator that can interpret product documentation and execute automated tests using ReWOO (Reasoning-without-Observation) agents orchestrated via LangGraph v1 alpha with Model Context Protocol (MCP) tooling.
- **Primary Outputs:** Test strategy plan, manual and automation test cases, execution artifacts (logs, screenshots, video), locator self-healing proposals, stability insights.
- **Automation Targets:** One web application (Playwright) and one mobile application (Appium), each with ≥5 user stories.
- **Success Metrics:**
  - Test planning turnaround ≤30s.
  - ≥80% requirement coverage by generated test cases.
  - ≥70% pass rate on first automation run.
  - ≤10% flaky rerun rate.
  - End-to-end execution for 10 cases completes in <5 minutes.

## Architecture Overview
- **Agent Pattern:** ReWOO with dedicated Planner, ToolSpec Emitter, Worker, Solver (Synthesizer) roles leveraging variable substitution to minimize planner calls.
- **Orchestration Layer:** LangGraph v1 alpha durable graph with checkpoints and immutable state log.
- **Tool Interface:** MCP servers for Playwright, Appium, filesystem, artifact store, Git, and issue tracker (optional).
- **Execution Backends:** Playwright (web) and Appium (mobile) for test runs, evidence capture, and locator verification.

### LangGraph Node Flow
1. `ingest_docs`
2. `planner`
3. `emit_tool_specs`
4. `dispatch_tools`
5. `substitute_vars`
6. `synthesize_artifacts`
7. `worker_execute_suite`
8. `collect_evidence`
9. `resolver`
10. `postmortem_and_heal`

Checkpoints are taken after `planner`, `synthesize_artifacts`, and `worker_execute_suite`.

## Deliverables
1. ReWOO orchestrator implementation with MCP tool integrations.
2. Generated artifacts: strategy, test suites (manual + automation), run reports, evidence bundles, self-heal proposals.
3. Environment profiles and tool registry configurations.
4. Operational runbook, troubleshooting guide, and acceptance checklist.

## Work Breakdown Structure

### Track A — Project & Environments
- **A1. Define POC boundaries and KPIs**
  - Select web and mobile targets (≥5 user stories each) and document scope with success metrics.
- **A2. Environment profiles**
  - Create profiles `web-local`, `web-ci`, `mobile-emu`, `mobile-device` with browser/device matrix, media toggles, and network throttles.
- **A3. MCP tooling registry**
  - Register MCP servers (filesystem, Playwright, Appium, artifact store, Git, issue tracker) with metadata, rate limits, and timeouts.

### Track B — Document Ingestion & Normalization
- **B1. Source connectors & parsing**
  - Accept Markdown, HTML, Confluence export, PDF, OpenAPI, and ticket data; produce unified Doc Pack.
- **B2. Requirement extraction & traceability skeleton**
  - Extract requirements and acceptance criteria; map to placeholder tests in a traceability index (≥90% coverage).

### Track C — ReWOO Agent Planning (No Observation)
- **C1. Planner prompt spec**
  - Output strategy, ≥8 sub-questions, variables, and dependency DAG for sample Doc Pack.
- **C2. ToolSpec emission**
  - Associate each sub-question with ToolSpec metadata (tool name, I/O, quality gates, timeouts).
- **C3. Variable catalog**
  - Define variable schema, validation, and fallbacks for all planned variables.

### Track D — MCP Tool Execution
- **D1. ToolSpec to MCP contracts**
  - Map ToolSpecs to MCP methods with idempotent semantics.
- **D2. Execution dispatcher**
  - Orchestrate parallel execution respecting DAG dependencies; capture raw outputs and evidence URIs.
- **D3. Quality gates & retries**
  - Implement bounded retries with jitter and structured error reporting.

### Track E — Variable Substitution & Artifact Synthesis
- **E1. Variable substitution**
  - Resolve all variables; generate human-readable gap list for unresolved items.
- **E2. Artifact synthesis**
  - Produce test plan, manual steps, automation specs, and runbook referencing validated selectors.

### Track F — Execution & Evidence
- **F1. Suite execution controller**
  - Execute selected profile; capture status, duration, retries, logs, screenshots, video.
- **F2. Flake probe**
  - Auto-rerun failures; classify instability causes.
- **F3. Reporting**
  - Provide summary with coverage, top failures, stability metrics, evidence links.

### Track G — Self-Healing & Feedback
- **G1. Locator drift detection**
  - Generate alternative selectors using attribute, text, and DOM proximity heuristics.
- **G2. Healed-run simulation**
  - Validate candidate selectors via dry-run and full rerun; configure approval criteria.
- **G3. Learning store**
  - Persist selector history and outcomes for future runs.

### Track H — Governance, Observability, Safety
- **H1. Audit log & provenance**
  - Record prompts, ToolSpecs, executions, evidence, and decision links.
- **H2. Guardrails**
  - Enforce rate/time caps, kill-switch, deny-list; verify via chaos test (<15s abort).
- **H3. Metrics**
  - Emit planning time, resolution rate, pass rate, flake rate, retries to dashboard or log dump.

## Data Contracts & Schemas
- **Doc Pack:** `{id, title, type, text, sections[], links[], entities[]}`
- **Requirement:** `{id, text, priority, tags[], acceptance[]}`
- **Plan:** `{strategy, risks[], priorities[], sub_questions[], variables[], dag_edges[]}`
- **ToolSpec:** `{id, tool, inputs:{…}, outputs:{…}, timeout_s, quality:{…}}`
- **Variable:** `{name, type, source_spec_id, validation:{…}, value?, evidence?}`
- **Manual Test:** `{id, requirement_ids[], steps[], expected[], data_matrix[]}`
- **Automation Spec:** `{id, ops:[], selectors, data_bindings}`
- **Execution Result:** `{test_id, status, duration_ms, retries, error?, evidence:{logs, screenshots[], video?}}`
- **Heal Proposal:** `{test_id, broken_selector, candidates[{selector, confidence, diff}]}`
- **Run Report:** `{summary, coverage, failures[], flakes[], links}`

## End-to-End Acceptance Test
1. Ingest 5 user stories + 1 API spec → generate plan with ≥8 sub-questions, variables, DAG.
2. Execute plan via MCP with ≥90% variable resolution on first pass.
3. Generate ≥12 tests (manual + automation) covering ≥80% requirements.
4. Run `web-local` suite achieving ≥70% pass rate with video and screenshot evidence.
5. Break 2 selectors → produce healed alternatives → rerun passes using fixes.
6. Final report shows coverage ≥80% and flake rate ≤10%.

## Risks & Mitigations
- **LangGraph alpha churn:** Pin versions; isolate prompts/configs.
- **Tool instability:** Apply conservative timeouts, retries, and evidence-first capture.
- **Doc noise:** Enforce document type tagging and whitelist critical requirements.
- **Over-healing:** Require A/B confirmation with repeated passes before persistence.

