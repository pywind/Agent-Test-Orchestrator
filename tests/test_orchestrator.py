from pathlib import Path

import pytest

from orchestrator.agent import run_orchestrator


@pytest.mark.parametrize("doc_path", ["examples/sample_docs/web_user_stories.md"])
def test_run_orchestrator(doc_path: str) -> None:
    outcome = run_orchestrator(doc_path)
    assert len(outcome.plan.sub_questions) >= 8
    assert len(outcome.tool_specs) == len(outcome.plan.sub_questions)
    resolved = [var for var in outcome.variables if var.status == "resolved"]
    assert len(resolved) >= int(0.9 * len(outcome.variables)) or len(outcome.variables) == 0
    assert len(outcome.artifacts.manual_tests) >= len(outcome.requirements)
    assert len(outcome.artifacts.automation_specs) >= len(outcome.requirements)
    assert outcome.metrics.execution_pass_rate >= 0.7 or outcome.metrics.flake_rate <= 0.1
    assert outcome.evidence_bundle.report.coverage >= 0.5
    assert outcome.evidence_bundle.heal_proposals
