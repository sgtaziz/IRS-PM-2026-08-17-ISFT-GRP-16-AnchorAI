from fastapi import APIRouter, HTTPException

from anchorai.knowledge.ego import EgoGraph, ego_graph
from anchorai.knowledge.graph import GraphUnavailable

router = APIRouter()


@router.get("/ego/{member_id}", response_model=EgoGraph)
def ego(member_id: str):
    try:
        graph = ego_graph(member_id)
    except GraphUnavailable:
        raise HTTPException(503, "Knowledge graph unavailable") from None
    if graph is None:
        raise HTTPException(404, f"Member {member_id} is not in the knowledge graph")
    return graph
