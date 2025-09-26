"""State and data contracts for the ReWOO testing orchestrator."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TypedDict


class DocumentType(str, Enum):
    """Supported source document types."""

    MARKDOWN = "markdown"
    HTML = "html"
    CONFLUENCE = "confluence"
    PDF = "pdf"
    OPENAPI = "openapi"
    TICKET = "ticket"


@dataclass
class Section:
    id: str
    title: str
    text: str


@dataclass
class DocPack:
    id: str
    title: str
    type: DocumentType
    text: str
    sections: List[Section] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)


@dataclass
class AcceptanceCriterion:
    id: str
    text: str


@dataclass
class Requirement:
    id: str
    text: str
    priority: str = "medium"
    tags: List[str] = field(default_factory=list)
    acceptance: List[AcceptanceCriterion] = field(default_factory=list)


@dataclass
class SubQuestion:
    id: str
    prompt: str
    depends_on: List[str] = field(default_factory=list)
    variable_refs: List[str] = field(default_factory=list)


@dataclass
class PlanVariable:
    name: str
    type: str
    description: str
    source_spec_id: Optional[str] = None
    validation: Dict[str, str] = field(default_factory=dict)
    value: Optional[str] = None
    evidence: Optional[str] = None
    fallback: Optional[str] = None
    status: str = "pending"


@dataclass
class Strategy:
    scope: List[str]
    risks: List[str]
    priorities: List[str]


@dataclass
class Plan:
    strategy: Strategy
    sub_questions: List[SubQuestion]
    variables: List[PlanVariable]
    dag_edges: List[List[str]]


@dataclass
class ToolIO:
    description: str
    schema: Dict[str, str] = field(default_factory=dict)


@dataclass
class ToolQualityGate:
    name: str
    condition: str
    on_failure: str


@dataclass
class ToolSpec:
    id: str
    tool: str
    inputs: ToolIO
    outputs: ToolIO
    timeout_s: int = 60
    quality: List[ToolQualityGate] = field(default_factory=list)
    cost_bound: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ManualTestStep:
    action: str
    expected: str


@dataclass
class ManualTest:
    id: str
    title: str
    requirement_ids: List[str]
    steps: List[ManualTestStep]
    data_matrix: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Operation:
    type: str
    selector: Optional[str] = None
    assertion: Optional[str] = None
    data_binding: Optional[str] = None


@dataclass
class AutomationSpec:
    id: str
    title: str
    requirement_ids: List[str]
    ops: List[Operation]
    selectors: Dict[str, str] = field(default_factory=dict)
    data_bindings: Dict[str, str] = field(default_factory=dict)


@dataclass
class TestPlanArtifact:
    scope: List[str]
    priorities: List[str]
    data_matrix: Dict[str, List[str]]
    environment_profile: str


@dataclass
class ExecutionEvidence:
    logs: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    video: Optional[str] = None


@dataclass
class ExecutionResult:
    test_id: str
    status: str
    duration_ms: int
    retries: int = 0
    error: Optional[str] = None
    evidence: ExecutionEvidence = field(default_factory=ExecutionEvidence)


@dataclass
class HealCandidate:
    selector: str
    confidence: float
    diff: str


@dataclass
class HealProposal:
    test_id: str
    broken_selector: str
    candidates: List[HealCandidate]


@dataclass
class RunReport:
    summary: str
    coverage: float
    failures: List[str]
    flakes: List[str]
    links: Dict[str, str] = field(default_factory=dict)


@dataclass
class TraceabilityEntry:
    requirement_id: str
    candidate_tests: List[str]


@dataclass
class TraceabilityIndex:
    entries: List[TraceabilityEntry]

    def coverage_ratio(self, total_requirements: int) -> float:
        if total_requirements == 0:
            return 0.0
        covered = sum(1 for entry in self.entries if entry.candidate_tests)
        return covered / total_requirements


@dataclass
class RunMetrics:
    planned_at: datetime
    planning_duration_s: float
    variable_resolution_rate: float
    execution_pass_rate: float
    flake_rate: float
    average_retry_count: float


@dataclass
class ArtifactBundle:
    test_plan: TestPlanArtifact
    manual_tests: List[ManualTest]
    automation_specs: List[AutomationSpec]
    runbook: str


@dataclass
class EvidenceBundle:
    results: List[ExecutionResult]
    report: RunReport
    heal_proposals: List[HealProposal]


@dataclass
class OrchestratorOutcome:
    doc_pack: DocPack
    requirements: List[Requirement]
    traceability: TraceabilityIndex
    plan: Plan
    tool_specs: List[ToolSpec]
    variables: List[PlanVariable]
    artifacts: ArtifactBundle
    evidence_bundle: EvidenceBundle
    metrics: RunMetrics

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class GraphState(TypedDict, total=False):
    doc_path: str
    doc_pack: DocPack
    requirements: List[Requirement]
    traceability: TraceabilityIndex
    plan: Plan
    tool_specs: List[ToolSpec]
    variables: Dict[str, PlanVariable]
    tool_results: Dict[str, Dict[str, str]]
    artifacts: ArtifactBundle
    execution_results: List[ExecutionResult]
    heal_proposals: List[HealProposal]
    run_report: RunReport
    metrics: RunMetrics
    planning_duration_s: float
    coverage: float
    gaps: List[str]
