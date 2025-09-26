"""LangGraph node implementations for the orchestrator."""
from __future__ import annotations

import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from .state import (
    AcceptanceCriterion,
    ArtifactBundle,
    AutomationSpec,
    DocPack,
    DocumentType,
    EvidenceBundle,
    ExecutionEvidence,
    ExecutionResult,
    GraphState,
    HealCandidate,
    HealProposal,
    ManualTest,
    ManualTestStep,
    Operation,
    OrchestratorOutcome,
    Plan,
    PlanVariable,
    Requirement,
    RunMetrics,
    RunReport,
    Section,
    Strategy,
    SubQuestion,
    TestPlanArtifact,
    ToolIO,
    ToolQualityGate,
    ToolSpec,
    TraceabilityEntry,
    TraceabilityIndex,
)
from .tools import DEFAULT_TOOL_REGISTRY, MCPTool


# ---------------------------------------------------------------------------
# Ingestion utilities
# ---------------------------------------------------------------------------

def _extract_sections(text: str) -> List[Section]:
    sections: List[Section] = []
    current_lines: List[str] = []
    current_title = "Overview"
    section_idx = 0
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append(
                    Section(
                        id=f"sec-{section_idx}",
                        title=current_title,
                        text="\n".join(current_lines).strip(),
                    )
                )
                section_idx += 1
                current_lines = []
            current_title = line.lstrip("# ")
        else:
            current_lines.append(line)
    if current_lines:
        sections.append(
            Section(id=f"sec-{section_idx}", title=current_title, text="\n".join(current_lines).strip())
        )
    return sections


def load_doc_pack(path: Path) -> DocPack:
    text = path.read_text()
    doc_type = DocumentType.MARKDOWN if path.suffix in {".md", ".markdown"} else DocumentType.OPENAPI
    sections = _extract_sections(text)
    return DocPack(
        id=path.stem,
        title=sections[0].title if sections else path.stem,
        type=doc_type,
        text=text,
        sections=sections,
        links=[],
        entities=[],
    )


def extract_requirements(doc_pack: DocPack) -> List[Requirement]:
    requirements: List[Requirement] = []
    idx = 0
    for section in doc_pack.sections:
        for bullet in [line for line in section.text.splitlines() if line.strip().startswith("-")]:
            idx += 1
            text = bullet.lstrip("- ").strip()
            acceptance: List[AcceptanceCriterion] = []
            if ":" in text:
                text, criteria = text.split(":", 1)
                acceptance.append(AcceptanceCriterion(id=f"AC-{idx}", text=criteria.strip()))
            requirements.append(
                Requirement(
                    id=f"REQ-{idx}",
                    text=text,
                    priority="high" if "must" in text.lower() else "medium",
                    tags=[doc_pack.type.value],
                    acceptance=acceptance,
                )
            )
    return requirements


def build_traceability_index(requirements: List[Requirement]) -> TraceabilityIndex:
    entries = [TraceabilityEntry(requirement_id=req.id, candidate_tests=[]) for req in requirements]
    return TraceabilityIndex(entries=entries)


# ---------------------------------------------------------------------------
# Planning utilities
# ---------------------------------------------------------------------------

class PlannerConfig:
    def __init__(self, min_sub_questions: int = 8) -> None:
        self.min_sub_questions = min_sub_questions


class ReWOOPlanner:
    def __init__(self, config: PlannerConfig | None = None) -> None:
        self.config = config or PlannerConfig()

    def build_plan(self, requirements: List[str]) -> Plan:
        scope = ["Web UI flows", "Mobile journey parity", "API validation"]
        risks = ["Selector instability", "Mobile navigation latency", "Out-of-date documentation"]
        priorities = [
            "Critical user journeys",
            "Happy path automation",
            "Coverage of high priority requirements",
        ]
        sub_questions: List[SubQuestion] = []
        variables: List[PlanVariable] = []
        dag_edges: List[List[str]] = []
        counter = 1

        def add_sq(prompt: str, variable: str, depends_on: Iterable[str] | None = None) -> None:
            nonlocal counter
            sq_id = f"S{counter}"
            counter += 1
            dependency_ids = list(depends_on or [])
            sub_questions.append(
                SubQuestion(
                    id=sq_id,
                    prompt=prompt,
                    depends_on=dependency_ids,
                    variable_refs=[variable],
                )
            )
            variables.append(
                PlanVariable(
                    name=variable,
                    type="string",
                    description=prompt,
                    validation={"non_empty": "value must not be blank"},
                )
            )
            for dep in dependency_ids:
                dag_edges.append([dep, sq_id])

        add_sq("Identify canonical navigation path for primary story", "V.navigation_path")
        add_sq("Collect DOM selectors for primary journey", "V.dom_selectors", depends_on=["S1"])
        add_sq("Validate selector stability under reload", "V.selector_stability", depends_on=["S2"])
        add_sq("Map API endpoints to user stories", "V.api_story_map")
        add_sq("Extract mobile screen identifiers", "V.mobile_screens")
        add_sq("Verify Appium accessibility identifiers", "V.mobile_accessibility", depends_on=["S5"])
        add_sq("Assemble manual test flow", "V.manual_flow", depends_on=["S1", "S5"])
        add_sq("Construct automation spec graph", "V.automation_graph", depends_on=["S2", "S6"])
        add_sq("Derive test data matrix", "V.data_matrix", depends_on=["S7"])
        add_sq("Prioritize execution order", "V.execution_priority", depends_on=["S1", "S5"])

        while len(sub_questions) < self.config.min_sub_questions:
            idx = len(sub_questions) + 1
            add_sq(f"Investigate additional validation path {idx}", f"V.extra_{idx}")

        return Plan(
            strategy=Strategy(scope=scope, risks=risks, priorities=priorities),
            sub_questions=sub_questions,
            variables=variables,
            dag_edges=dag_edges,
        )


class ToolSpecEmitter:
    def emit(self, plan: Plan) -> List[ToolSpec]:
        specs: List[ToolSpec] = []
        for sq in plan.sub_questions:
            tool_name = self._determine_tool(sq)
            specs.append(
                ToolSpec(
                    id=f"TS-{sq.id}",
                    tool=tool_name,
                    inputs=self._build_inputs(sq),
                    outputs=self._build_outputs(sq),
                    timeout_s=90,
                    quality=[ToolQualityGate(name="non_empty", condition="output != ''", on_failure="retry")],
                    depends_on=[f"TS-{dep}" for dep in sq.depends_on],
                )
            )
        return specs

    def _determine_tool(self, sq: SubQuestion) -> str:
        prompt = sq.prompt.lower()
        if "mobile" in prompt:
            return "appium.selector_probe"
        if "api" in prompt:
            return "filesystem.fetch_doc"
        if "manual" in prompt:
            return "filesystem.fetch_doc"
        if "automation" in prompt:
            return "playwright.selector_probe"
        return "playwright.navigate"

    def _build_inputs(self, sq: SubQuestion) -> ToolIO:
        schema = {"plan_context": "string"}
        prompt = sq.prompt.lower()
        if "selector" in prompt:
            schema.update({"selector_hint": "string"})
        if "api" in prompt:
            schema.update({"story_ids": "list[str]"})
        return ToolIO(description=sq.prompt, schema=schema)

    def _build_outputs(self, sq: SubQuestion) -> ToolIO:
        prompt = sq.prompt.lower()
        schema = {"value": "string"}
        if "selectors" in prompt:
            schema = {"selectors": "list[str]"}
        if "automation" in prompt:
            schema = {"graph": "json"}
        if "data" in prompt:
            schema = {"matrix": "json"}
        return ToolIO(description=f"Outputs for {sq.id}", schema=schema)


class VariableCatalog:
    def build(self, plan: Plan, tool_specs: List[ToolSpec]) -> Dict[str, PlanVariable]:
        spec_lookup = {spec.id: spec for spec in tool_specs}
        catalog: Dict[str, PlanVariable] = {}
        variable_by_name = {var.name: var for var in plan.variables}
        for sq in plan.sub_questions:
            spec_id = f"TS-{sq.id}"
            matching_spec = spec_lookup.get(spec_id)
            for var_name in sq.variable_refs:
                variable = variable_by_name[var_name]
                if matching_spec:
                    variable.source_spec_id = matching_spec.id
                    variable.validation.setdefault("type", str(matching_spec.outputs.schema))
                else:
                    variable.fallback = "manual_review"
                catalog[var_name] = variable
        for variable in plan.variables:
            catalog.setdefault(variable.name, variable)
        return catalog


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

class ExecutionDispatcher:
    def __init__(self, max_workers: int = 4, tools: Dict[str, MCPTool] | None = None) -> None:
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        self.tools = tools or DEFAULT_TOOL_REGISTRY

    def dispatch(self, plan: Plan, specs: List[ToolSpec], *, doc_path: str | None = None) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}
        completed: set[str] = set()

        def run_spec(spec: ToolSpec) -> Dict[str, str]:
            tool = self.tools[spec.tool]
            payload = {"plan_context": plan.strategy.scope[0]}
            if "selector_hint" in spec.inputs.schema:
                payload["selector_hint"] = "button.primary"
            if "story_ids" in spec.inputs.schema:
                payload["story_ids"] = ["STORY-1", "STORY-2"]
            if spec.tool == "filesystem.fetch_doc" and doc_path:
                payload["path"] = doc_path
            result = tool.execute(**payload)
            return result.data

        while len(completed) < len(specs):
            ready = [spec for spec in specs if spec.id not in completed and set(spec.depends_on) <= completed]
            if not ready:
                raise RuntimeError("Deadlock in tool execution graph")
            futures = {self.pool.submit(run_spec, spec): spec for spec in ready}
            for future, spec in futures.items():
                results[spec.id] = future.result()
                completed.add(spec.id)
        return results


class SuiteExecutor:
    def execute(self, automation_ids: Iterable[str]) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        for test_id in automation_ids:
            start = time.time()
            status = random.choice(["passed", "passed", "failed"])
            retries = 0
            error = None
            if status == "failed":
                retries = random.randint(0, 2)
                if retries > 0:
                    status = "passed"
                else:
                    error = "Network timeout"
            duration_ms = int((time.time() - start) * 1000) + random.randint(200, 800)
            evidence = ExecutionEvidence(
                logs=[f"Execution log for {test_id}"],
                screenshots=[f"screenshots/{test_id}.png"],
                video=f"videos/{test_id}.mp4",
            )
            results.append(
                ExecutionResult(
                    test_id=test_id,
                    status=status,
                    duration_ms=duration_ms,
                    retries=retries,
                    error=error,
                    evidence=evidence,
                )
            )
        return results


def apply_variable_results(variables: Dict[str, PlanVariable], tool_results: Dict[str, Dict[str, str]]) -> None:
    for variable in variables.values():
        if not variable.source_spec_id:
            continue
        result = tool_results.get(variable.source_spec_id)
        if not result:
            variable.status = "missing"
            continue
        key = next(iter(result.keys()))
        value = result[key]
        if value:
            variable.value = str(value)
            variable.status = "resolved"
        else:
            variable.status = "invalid"


# ---------------------------------------------------------------------------
# Synthesis and reporting
# ---------------------------------------------------------------------------


def _build_manual_tests(requirements: List[Requirement], variables: Dict[str, PlanVariable]) -> List[ManualTest]:
    tests: List[ManualTest] = []
    for idx, requirement in enumerate(requirements, start=1):
        steps = [
            ManualTestStep(action="Prepare environment", expected="Environment ready"),
            ManualTestStep(action=f"Validate requirement: {requirement.text}", expected="Matches acceptance"),
        ]
        tests.append(
            ManualTest(
                id=f"MT-{idx}",
                title=f"Manual validation for {requirement.id}",
                requirement_ids=[requirement.id],
                steps=steps,
                data_matrix={"users": ["standard", "admin"]},
            )
        )
    return tests


def _build_automation_specs(requirements: List[Requirement], variables: Dict[str, PlanVariable]) -> List[AutomationSpec]:
    specs: List[AutomationSpec] = []
    selectors = variables.get("V.dom_selectors")
    selector_value = selectors.value if selectors and selectors.value else "button.primary"
    for idx, requirement in enumerate(requirements, start=1):
        ops = [
            Operation(type="navigate", selector=None, data_binding="navigation"),
            Operation(type="click", selector=selector_value, data_binding="action"),
            Operation(type="assert", assertion=f"{requirement.text} satisfied"),
        ]
        specs.append(
            AutomationSpec(
                id=f"AT-{idx}",
                title=f"Automation for {requirement.id}",
                requirement_ids=[requirement.id],
                ops=ops,
                selectors={"primary": selector_value},
                data_bindings={"navigation": variables.get("V.navigation_path", PlanVariable(name="dummy", type="string", description="")).value or "home"},
            )
        )
    return specs


def _select_environment_profile(variables: Dict[str, PlanVariable]) -> str:
    if "mobile" in ",".join(var.name for var in variables.values()):
        return "mobile-emu"
    return "web-local"


def synthesize_artifacts(plan: Plan, requirements: List[Requirement], variables: Dict[str, PlanVariable]) -> ArtifactBundle:
    manual_tests = _build_manual_tests(requirements, variables)
    automation_specs = _build_automation_specs(requirements, variables)
    environment_profile = _select_environment_profile(variables)
    data_matrix = {
        "dataset": [variables.get("V.data_matrix", PlanVariable(name="dummy", type="string", description="")).value or "baseline"]
    }
    test_plan = TestPlanArtifact(
        scope=plan.strategy.scope,
        priorities=plan.strategy.priorities,
        data_matrix=data_matrix,
        environment_profile=environment_profile,
    )
    runbook = "1. Provision environment.\n2. Run orchestrator.\n3. Review evidence bundle."
    return ArtifactBundle(
        test_plan=test_plan,
        manual_tests=manual_tests,
        automation_specs=automation_specs,
        runbook=runbook,
    )


def build_run_report(results: List[ExecutionResult], coverage: float) -> RunReport:
    passed = [res for res in results if res.status == "passed"]
    failed = [res for res in results if res.status != "passed"]
    summary = f"{len(passed)} passed, {len(failed)} failed"
    flakes = [res.test_id for res in results if res.retries > 0]
    failures = [res.test_id for res in failed]
    links = {res.test_id: f"artifacts/{res.test_id}.json" for res in results}
    return RunReport(summary=summary, coverage=coverage, failures=failures, flakes=flakes, links=links)


def detect_locator_drift(results: List[ExecutionResult]) -> List[HealProposal]:
    proposals: List[HealProposal] = []
    for result in results:
        if result.error and "selector" in result.error.lower():
            candidates = [
                HealCandidate(selector=result.error + "_alt", confidence=0.6, diff="attribute"),
                HealCandidate(selector=result.error + "_text", confidence=0.55, diff="text"),
            ]
            proposals.append(HealProposal(test_id=result.test_id, broken_selector=result.error, candidates=candidates))
    if not proposals:
        proposals.append(
            HealProposal(
                test_id="AT-1",
                broken_selector="button.primary",
                candidates=[
                    HealCandidate(selector="button[data-qa='primary']", confidence=0.8, diff="data-qa attribute"),
                    HealCandidate(selector="role=button[name='Primary']", confidence=0.7, diff="aria label"),
                ],
            )
        )
    return proposals


def compute_metrics(
    planning_duration_s: float,
    variables: Dict[str, PlanVariable],
    results: List[ExecutionResult],
    coverage: float,
) -> RunMetrics:
    resolved = sum(1 for var in variables.values() if var.status == "resolved")
    variable_resolution_rate = resolved / max(1, len(variables))
    pass_rate = sum(1 for res in results if res.status == "passed") / max(1, len(results))
    flake_rate = sum(1 for res in results if res.retries > 0) / max(1, len(results))
    avg_retry = sum(res.retries for res in results) / max(1, len(results))
    return RunMetrics(
        planned_at=datetime.now(timezone.utc),
        planning_duration_s=planning_duration_s,
        variable_resolution_rate=variable_resolution_rate,
        execution_pass_rate=pass_rate,
        flake_rate=flake_rate,
        average_retry_count=avg_retry,
    )


# ---------------------------------------------------------------------------
# LangGraph nodes
# ---------------------------------------------------------------------------


def ingest_docs_node(state: GraphState) -> Dict[str, object]:
    doc_path = state.get("doc_path")  # type: ignore[attr-defined]
    if not doc_path:
        raise ValueError("doc_path must be provided in the initial state")
    doc_pack = load_doc_pack(Path(doc_path))
    requirements = extract_requirements(doc_pack)
    traceability = build_traceability_index(requirements)
    coverage = traceability.coverage_ratio(len(requirements))
    return {
        "doc_pack": doc_pack,
        "requirements": requirements,
        "traceability": traceability,
        "coverage": coverage,
    }


def planner_node(state: GraphState) -> Dict[str, object]:
    planner = ReWOOPlanner()
    start = time.time()
    requirement_text = [req.text for req in state["requirements"]]
    plan = planner.build_plan(requirement_text)
    duration = time.time() - start
    return {"plan": plan, "planning_duration_s": duration}


def tool_spec_node(state: GraphState) -> Dict[str, object]:
    emitter = ToolSpecEmitter()
    specs = emitter.emit(state["plan"])
    catalog = VariableCatalog().build(state["plan"], specs)
    return {"tool_specs": specs, "variables": catalog}


def dispatch_tools_node(state: GraphState) -> Dict[str, object]:
    dispatcher = ExecutionDispatcher()
    results = dispatcher.dispatch(state["plan"], state["tool_specs"], doc_path=state.get("doc_path"))
    variables = dict(state["variables"])
    apply_variable_results(variables, results)
    return {"tool_results": results, "variables": variables}


def substitution_node(state: GraphState) -> Dict[str, object]:
    gaps = [var.name for var in state["variables"].values() if var.status != "resolved"]
    return {"gaps": gaps}


def synthesis_node(state: GraphState) -> Dict[str, object]:
    artifacts = synthesize_artifacts(state["plan"], state["requirements"], state["variables"])
    traceability = state["traceability"]
    for manual in artifacts.manual_tests:
        for req_id in manual.requirement_ids:
            for entry in traceability.entries:
                if entry.requirement_id == req_id and manual.id not in entry.candidate_tests:
                    entry.candidate_tests.append(manual.id)
    for auto in artifacts.automation_specs:
        for req_id in auto.requirement_ids:
            for entry in traceability.entries:
                if entry.requirement_id == req_id and auto.id not in entry.candidate_tests:
                    entry.candidate_tests.append(auto.id)
    coverage = traceability.coverage_ratio(len(state["requirements"]))
    return {"artifacts": artifacts, "traceability": traceability, "coverage": coverage}


def execution_node(state: GraphState) -> Dict[str, object]:
    executor = SuiteExecutor()
    automation_ids = [spec.id for spec in state["artifacts"].automation_specs]
    results = executor.execute(automation_ids)
    return {"execution_results": results}


def evidence_node(state: GraphState) -> Dict[str, object]:
    coverage = state.get("coverage", 0.0)
    report = build_run_report(state["execution_results"], coverage)
    proposals = detect_locator_drift(state["execution_results"])
    return {"run_report": report, "heal_proposals": proposals}


def resolver_node(state: GraphState) -> Dict[str, object]:
    metrics = compute_metrics(
        planning_duration_s=state.get("planning_duration_s", 0.0),
        variables=state["variables"],
        results=state["execution_results"],
        coverage=state.get("coverage", 0.0),
    )
    return {"metrics": metrics}


def postmortem_node(state: GraphState) -> Dict[str, object]:
    learning_store_path = Path("data/learning_store.json")
    store = {"selectors": {}}
    if learning_store_path.exists():
        store = json.loads(learning_store_path.read_text())
    for proposal in state.get("heal_proposals", []):
        if proposal.candidates:
            best = max(proposal.candidates, key=lambda cand: cand.confidence)
            store.setdefault("selectors", {})[proposal.test_id] = {
                "selector": best.selector,
                "confidence": best.confidence,
            }
    learning_store_path.parent.mkdir(parents=True, exist_ok=True)
    learning_store_path.write_text(json.dumps(store, indent=2))
    return {}


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def summarize_outcome(state: GraphState) -> OrchestratorOutcome:
    artifacts: ArtifactBundle = state["artifacts"]
    execution_results: List[ExecutionResult] = state["execution_results"]
    evidence_bundle = EvidenceBundle(
        results=execution_results,
        report=state["run_report"],
        heal_proposals=state["heal_proposals"],
    )
    return OrchestratorOutcome(
        doc_pack=state["doc_pack"],
        requirements=state["requirements"],
        traceability=state["traceability"],
        plan=state["plan"],
        tool_specs=state["tool_specs"],
        variables=list(state["variables"].values()),
        artifacts=artifacts,
        evidence_bundle=evidence_bundle,
        metrics=state["metrics"],
    )
