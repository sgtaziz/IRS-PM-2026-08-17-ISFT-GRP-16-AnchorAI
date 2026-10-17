"""A member, class or instructor neighbourhood in Cytoscape's elements format."""

from typing import Any, Literal

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
    member_total: int | None = None


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


EgoKind = Literal["member", "class", "instructor"]
MEMBER_CAP = 40

_QUERIES = {
    "member": (queries.EGO, "member_id"),
    "class": (queries.EGO_CLASS, "class_id"),
    "instructor": (queries.EGO_INSTRUCTOR, "instructor_id"),
}


def ego_graph(
    entity_id: str, driver: Driver | None = None, kind: EgoKind = "member"
) -> EgoGraph | None:
    """Class and instructor graphs show at most MEMBER_CAP members; member_total is the full count."""
    query, param = _QUERIES[kind]
    params: dict[str, Any] = {param: entity_id}
    if kind != "member":
        params["cap"] = MEMBER_CAP
    records = read_records(query, driver, **params)
    if not records:
        return None
    nodes: dict[str, Element] = {}
    edges: dict[str, Element] = {}
    root = records[0]["root"]
    nodes[root.element_id] = _node(root)
    for path in records[0]["paths"]:
        for n in path.nodes:
            nodes.setdefault(n.element_id, _node(n))
        for r in path.relationships:
            edges.setdefault(r.element_id, _edge(r))
    return EgoGraph(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        member_total=records[0].get("member_total"),
    )
