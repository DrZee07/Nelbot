from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Type,
    TypedDict,
    Union,
    overload,
)
from uuid import UUID, uuid4

from langchain_core.pydantic_v1 import BaseModel
from langchain_core.runnables.graph_ascii import draw_ascii

if TYPE_CHECKING:
    from langchain_core.runnables.base import Runnable as RunnableType


class LabelsDict(TypedDict):
    nodes: dict[str, str]
    edges: dict[str, str]


def is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


class Edge(NamedTuple):
    """Edge in a graph."""

    source: str
    target: str
    data: Optional[str] = None


class Node(NamedTuple):
    """Node in a graph."""

    id: str
    data: Union[Type[BaseModel], RunnableType]


def node_data_str(node: Node) -> str:
    from langchain_core.runnables.base import Runnable

    if not is_uuid(node.id):
        return node.id
    elif isinstance(node.data, Runnable):
        try:
            data = str(node.data)
            if (
                data.startswith("<")
                or data[0] != data[0].upper()
                or len(data.splitlines()) > 1
            ):
                data = node.data.__class__.__name__
            elif len(data) > 42:
                data = data[:42] + "..."
        except Exception:
            data = node.data.__class__.__name__
    else:
        data = node.data.__name__
    return data if not data.startswith("Runnable") else data[8:]


def node_data_json(node: Node) -> Dict[str, Union[str, Dict[str, Any]]]:
    from langchain_core.load.serializable import to_json_not_implemented
    from langchain_core.runnables.base import Runnable, RunnableSerializable

    if isinstance(node.data, RunnableSerializable):
        return {
            "type": "runnable",
            "data": {
                "id": node.data.lc_id(),
                "name": node.data.get_name(),
            },
        }
    elif isinstance(node.data, Runnable):
        return {
            "type": "runnable",
            "data": {
                "id": to_json_not_implemented(node.data)["id"],
                "name": node.data.get_name(),
            },
        }
    elif inspect.isclass(node.data) and issubclass(node.data, BaseModel):
        return {
            "type": "schema",
            "data": node.data.schema(),
        }
    else:
        return {
            "type": "unknown",
            "data": node_data_str(node),
        }


@dataclass
class Graph:
    """Graph of nodes and edges."""

    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def to_json(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert the graph to a JSON-serializable format."""
        stable_node_ids = {
            node.id: i if is_uuid(node.id) else node.id
            for i, node in enumerate(self.nodes.values())
        }

        return {
            "nodes": [
                {"id": stable_node_ids[node.id], **node_data_json(node)}
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": stable_node_ids[edge.source],
                    "target": stable_node_ids[edge.target],
                    "data": edge.data,
                }
                if edge.data is not None
                else {
                    "source": stable_node_ids[edge.source],
                    "target": stable_node_ids[edge.target],
                }
                for edge in self.edges
            ],
        }

    def __bool__(self) -> bool:
        return bool(self.nodes)

    def next_id(self) -> str:
        return uuid4().hex

    def add_node(
        self, data: Union[Type[BaseModel], RunnableType], id: Optional[str] = None
    ) -> Node:
        """Add a node to the graph and return it."""
        if id is not None and id in self.nodes:
            raise ValueError(f"Node with id {id} already exists")
        node = Node(id=id or self.next_id(), data=data)
        self.nodes[node.id] = node
        return node

    def remove_node(self, node: Node) -> None:
        """Remove a node from the graphm and all edges connected to it."""
        self.nodes.pop(node.id)
        self.edges = [
            edge
            for edge in self.edges
            if edge.source != node.id and edge.target != node.id
        ]

    def add_edge(self, source: Node, target: Node, data: Optional[str] = None) -> Edge:
        """Add an edge to the graph and return it."""
        if source.id not in self.nodes:
            raise ValueError(f"Source node {source.id} not in graph")
        if target.id not in self.nodes:
            raise ValueError(f"Target node {target.id} not in graph")
        edge = Edge(source=source.id, target=target.id, data=data)
        self.edges.append(edge)
        return edge

    def extend(self, graph: Graph) -> None:
        """Add all nodes and edges from another graph.
        Note this doesn't check for duplicates, nor does it connect the graphs."""
        self.nodes.update(graph.nodes)
        self.edges.extend(graph.edges)

    def first_node(self) -> Optional[Node]:
        """Find the single node that is not a target of any edge.
        If there is no such node, or there are multiple, return None.
        When drawing the graph this node would be the origin."""
        targets = {edge.target for edge in self.edges}
        found: List[Node] = []
        for node in self.nodes.values():
            if node.id not in targets:
                found.append(node)
        return found[0] if len(found) == 1 else None

    def last_node(self) -> Optional[Node]:
        """Find the single node that is not a source of any edge.
        If there is no such node, or there are multiple, return None.
        When drawing the graph this node would be the destination.
        """
        sources = {edge.source for edge in self.edges}
        found: List[Node] = []
        for node in self.nodes.values():
            if node.id not in sources:
                found.append(node)
        return found[0] if len(found) == 1 else None

    def trim_first_node(self) -> None:
        """Remove the first node if it exists and has a single outgoing edge,
        ie. if removing it would not leave the graph without a "first" node."""
        first_node = self.first_node()
        if first_node:
            if (
                len(self.nodes) == 1
                or len([edge for edge in self.edges if edge.source == first_node.id])
                == 1
            ):
                self.remove_node(first_node)

    def trim_last_node(self) -> None:
        """Remove the last node if it exists and has a single incoming edge,
        ie. if removing it would not leave the graph without a "last" node."""
        last_node = self.last_node()
        if last_node:
            if (
                len(self.nodes) == 1
                or len([edge for edge in self.edges if edge.target == last_node.id])
                == 1
            ):
                self.remove_node(last_node)

    def draw_ascii(self) -> str:
        return draw_ascii(
            {node.id: node_data_str(node) for node in self.nodes.values()},
            [(edge.source, edge.target) for edge in self.edges],
        )

    def print_ascii(self) -> None:
        print(self.draw_ascii())  # noqa: T201

    @overload
    def draw_png(
        self,
        output_file_path: str,
        fontname: Optional[str] = None,
        labels: Optional[LabelsDict] = None,
    ) -> None:
        ...

    @overload
    def draw_png(
        self,
        output_file_path: None,
        fontname: Optional[str] = None,
        labels: Optional[LabelsDict] = None,
    ) -> bytes:
        ...

    def draw_png(
        self,
        output_file_path: Optional[str] = None,
        fontname: Optional[str] = None,
        labels: Optional[LabelsDict] = None,
    ) -> Union[bytes, None]:
        from langchain_core.runnables.graph_png import PngDrawer

        return PngDrawer(fontname, labels).draw(self, output_file_path)
