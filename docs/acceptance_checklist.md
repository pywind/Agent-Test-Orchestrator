# Acceptance Test Checklist

- [ ] Ingest 5+ user stories and API specification into Doc Pack using `load_doc_pack`.
- [ ] Planner outputs ≥8 sub-questions, variables, and DAG edges for the sample Doc Pack.
- [ ] ToolSpec emitter assigns ToolSpecs with timeout and quality gates to each sub-question.
- [ ] Dispatcher resolves ≥90% variables on first execution pass.
- [ ] Artifact synthesis produces test plan, ≥12 manual/automation tests combined, and runbook.
- [ ] Suite execution generates junit-style metrics including status, duration, retries, and evidence URIs.
- [ ] Flake probe reruns failed tests and reports instability causes.
- [ ] Run report summarizes pass/fail, coverage ≥80%, and flake rate ≤10%.
- [ ] Locator healing proposals contain ≥1 alternative selector with confidence score.
- [ ] Learning store updated with accepted selectors after successful reruns.
