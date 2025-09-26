"""LangGraph graph assembly for the ReWOO testing orchestrator."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from langgraph.graph import END, StateGraph

from .utils.nodes import (
    dispatch_tools_node,
    evidence_node,
    execution_node,
    ingest_docs_node,
    planner_node,
    postmortem_node,
    resolver_node,
    summarize_outcome,
    synthesis_node,
    substitution_node,
    tool_spec_node,
)
from .utils.state import GraphState, OrchestratorOutcome


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("ingest_docs", ingest_docs_node)
    graph.add_node("planner", planner_node)
    graph.add_node("emit_tool_specs", tool_spec_node)
    graph.add_node("dispatch_tools", dispatch_tools_node)
    graph.add_node("substitute_vars", substitution_node)
    graph.add_node("synthesize_artifacts", synthesis_node)
    graph.add_node("worker_execute_suite", execution_node)
    graph.add_node("collect_evidence", evidence_node)
    graph.add_node("resolver", resolver_node)
    graph.add_node("postmortem_and_heal", postmortem_node)

    graph.set_entry_point("ingest_docs")
    graph.add_edge("ingest_docs", "planner")
    graph.add_edge("planner", "emit_tool_specs")
    graph.add_edge("emit_tool_specs", "dispatch_tools")
    graph.add_edge("dispatch_tools", "substitute_vars")
    graph.add_edge("substitute_vars", "synthesize_artifacts")
    graph.add_edge("synthesize_artifacts", "worker_execute_suite")
    graph.add_edge("worker_execute_suite", "collect_evidence")
    graph.add_edge("collect_evidence", "resolver")
    graph.add_edge("resolver", "postmortem_and_heal")
    graph.add_edge("postmortem_and_heal", END)

    return graph


def run_orchestrator(doc_path: str) -> OrchestratorOutcome:
    graph = build_graph()
    app = graph.compile()
    initial_state: Dict[str, object] = {"doc_path": doc_path}
    final_state = app.invoke(initial_state)  # type: ignore[arg-type]
    return summarize_outcome(final_state)


def run_cli(doc: str) -> OrchestratorOutcome:
    resolved_path = str(Path(doc))
    return run_orchestrator(resolved_path)
