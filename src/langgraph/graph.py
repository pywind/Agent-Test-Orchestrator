"""Minimal StateGraph implementation for unit testing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, MutableMapping

END = "__end__"


@dataclass
class _CompiledGraph:
    entry_point: str
    edges: Mapping[str, List[str]]
    nodes: Mapping[str, Callable[[MutableMapping[str, object]], Dict[str, object]]]

    def invoke(self, state: MutableMapping[str, object]) -> MutableMapping[str, object]:
        context: MutableMapping[str, object] = dict(state)
        current = self.entry_point
        visited: set[str] = set()
        while current != END:
            if current in visited:
                raise RuntimeError(f"Cycle detected at node {current}")
            visited.add(current)
            node_fn = self.nodes.get(current)
            if node_fn is None:
                raise KeyError(f"Node {current} not defined")
            updates = node_fn(context)
            if updates:
                context.update(updates)
            next_nodes = self.edges.get(current, [])
            if not next_nodes:
                raise RuntimeError(f"Node {current} has no outgoing edge")
            if len(next_nodes) > 1:
                raise RuntimeError("Branching execution is not supported in the stub")
            current = next_nodes[0]
        return context


class StateGraph:
    """Highly simplified subset of LangGraph's StateGraph."""

    def __init__(self, _state_type: object) -> None:
        self._nodes: Dict[str, Callable[[MutableMapping[str, object]], Dict[str, object]]] = {}
        self._edges: Dict[str, List[str]] = {}
        self._entry_point: str | None = None

    def add_node(self, name: str, func: Callable[[MutableMapping[str, object]], Dict[str, object]]) -> None:
        self._nodes[name] = func

    def set_entry_point(self, name: str) -> None:
        if name not in self._nodes:
            raise KeyError(f"Entry point {name} must be registered before use")
        self._entry_point = name

    def add_edge(self, start: str, end: str) -> None:
        if start not in self._nodes and start != END:
            raise KeyError(f"Start node {start} not defined")
        if end != END and end not in self._nodes:
            raise KeyError(f"End node {end} not defined")
        self._edges.setdefault(start, []).append(end)

    def compile(self) -> _CompiledGraph:
        if self._entry_point is None:
            raise RuntimeError("Entry point must be set before compiling the graph")
        return _CompiledGraph(entry_point=self._entry_point, edges=self._edges, nodes=self._nodes)
