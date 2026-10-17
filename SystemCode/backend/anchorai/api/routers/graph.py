from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from anchorai.api.deps import SessionDep, require_role
from anchorai.discovery.service import DataNotBuilt
from anchorai.knowledge import simulate
from anchorai.knowledge.ego import EgoGraph, ego_graph
from anchorai.knowledge.graph import GraphReloading, GraphUnavailable
from anchorai.knowledge.simulate import Entities, EventType, Simulation

router = APIRouter()


def _unavailable(e: Exception) -> str:
    return (
        "Knowledge graph is reloading"
        if isinstance(e, GraphReloading)
        else "Knowledge graph unavailable"
    )


manager_up = [Depends(require_role("manager", "admin"))]


class SimulateRequest(BaseModel):
    event_type: EventType
    entity_id: str


@router.get("/ego/{member_id}", response_model=EgoGraph)
def ego(member_id: str):
    try:
        graph = ego_graph(member_id)
    except GraphUnavailable as e:
        raise HTTPException(503, _unavailable(e)) from None
    if graph is None:
        raise HTTPException(404, f"Member {member_id} is not in the knowledge graph")
    return graph


@router.get("/ego/{kind}/{entity_id}", response_model=EgoGraph, dependencies=manager_up)
def ego_entity(kind: Literal["class", "instructor"], entity_id: str):
    try:
        graph = ego_graph(entity_id, kind=kind)
    except GraphUnavailable as e:
        raise HTTPException(503, _unavailable(e)) from None
    if graph is None:
        raise HTTPException(404, f"{kind.capitalize()} {entity_id} is not in the knowledge graph")
    return graph


@router.get("/entities", response_model=Entities, dependencies=manager_up)
def entities(session: SessionDep):
    try:
        return simulate.entities(session)
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None


@router.post("/simulate", response_model=Simulation, dependencies=manager_up)
def simulate_event(req: SimulateRequest, session: SessionDep):
    try:
        result = simulate.simulate(session, req.event_type, req.entity_id)
    except DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None
    except GraphUnavailable as e:
        raise HTTPException(503, _unavailable(e)) from None
    if result is None:
        raise HTTPException(404, f"Unknown {req.event_type.split('_')[0]} {req.entity_id}")
    return result
