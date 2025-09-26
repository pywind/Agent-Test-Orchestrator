"""Celery task definitions for the asynchronous orchestrator workflow."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, cast

from celery import Celery

from .orchestrator.utils.nodes import (
    dispatch_tools_node,
    evidence_node,
    execution_node,
    ingest_docs_node,
    planner_node,
    postmortem_node,
    resolver_node,
    substitution_node,
    synthesis_node,
    tool_spec_node,
)
from .orchestrator.utils.state import GraphState


celery_app = Celery("agent_test_orchestrator", broker="memory://", backend="cache+memory://")
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    accept_content=["pickle", "json"],
    result_serializer="pickle",
    task_serializer="pickle",
)


def _next_state(state: GraphState, update: Dict[str, object]) -> GraphState:
    new_state = deepcopy(dict(state))
    new_state.update(update)
    return cast(GraphState, new_state)


@celery_app.task(name="orchestrator.ingest")
def ingest_task(doc_path: str) -> GraphState:
    state = cast(GraphState, {"doc_path": doc_path})
    updates = ingest_docs_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.plan")
def planner_task(state: GraphState) -> GraphState:
    updates = planner_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.emit_specs")
def tool_spec_task(state: GraphState) -> GraphState:
    updates = tool_spec_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.dispatch")
def dispatch_task(state: GraphState) -> GraphState:
    updates = dispatch_tools_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.substitute")
def substitution_task(state: GraphState) -> GraphState:
    updates = substitution_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.synthesize")
def synthesis_task(state: GraphState) -> GraphState:
    updates = synthesis_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.execute")
def execution_task(state: GraphState) -> GraphState:
    updates = execution_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.collect_evidence")
def evidence_task(state: GraphState) -> GraphState:
    updates = evidence_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.resolve")
def resolver_task(state: GraphState) -> GraphState:
    updates = resolver_node(state)
    return _next_state(state, updates)


@celery_app.task(name="orchestrator.postmortem")
def postmortem_task(state: GraphState) -> GraphState:
    updates = postmortem_node(state)
    return _next_state(state, updates)


__all__ = [
    "celery_app",
    "ingest_task",
    "planner_task",
    "tool_spec_task",
    "dispatch_task",
    "substitution_task",
    "synthesis_task",
    "execution_task",
    "evidence_task",
    "resolver_task",
    "postmortem_task",
]
