"""A member's neighbourhood in Cytoscape's elements format."""

from typing import Any

from neo4j import Driver
from neo4j.graph import Node, Relationship
from pydantic import BaseModel

from anchorai.knowledge import queries
from anchorai.knowledge.graph import read_records

LABEL_KEYS = {"Member": "member_id", "Club": "club_id", "Class": "name", "Instructor": "name"}


class Element(BaseModel):
    data: dict[str, Any]


class EgoGraph(BaseModel):
    nodes: list[Element]
    edges: list[Element]


def _plain(props: dict[str, Any]) -> dict[str, Any]:
    # Neo4j dates are not JSON-serialisable; ISO strings are what the UI shows anyway.
    return {k: v.iso_format() if hasattr(v, "iso_format") else v for k, v in props.items()}


def _node(n: Node) -> Element:
    kind = next(iter(n.labels))
    props = _plain(dict(n))
    label = props.get(LABEL_KEYS.get(kind, ""), props.get("name", props.get("type", kind)))
    return Element(data={**props, "id": n.element_id, "type": kind, "label": str(label)})


def _edge(r: Relationship) -> Element:
    return Element(
        data={
            **_plain(dict(r)),
            "id": r.element_id,
            "source": r.start_node.element_id,
            "target": r.end_node.element_id,
            "type": r.type,
        }
    )


def ego_graph(member_id: str, driver: Driver | None = None) -> EgoGraph | None:
    records = read_records(queries.EGO, driver, member_id=member_id)
    if not records:
        return None
    nodes: dict[str, Element] = {}
    edges: dict[str, Element] = {}
    member = records[0]["m"]
    nodes[member.element_id] = _node(member)
    for path in records[0]["paths"]:
        for n in path.nodes:
            nodes.setdefault(n.element_id, _node(n))
        for r in path.relationships:
            edges.setdefault(r.element_id, _edge(r))
    return EgoGraph(nodes=list(nodes.values()), edges=list(edges.values()))
