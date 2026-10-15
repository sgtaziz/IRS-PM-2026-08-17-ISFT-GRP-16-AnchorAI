from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from anchorai.api.deps import SessionDep, require_role
from anchorai.discovery import service
from anchorai.discovery.views import (
    Dashboard,
    Facets,
    MemberDetail,
    MemberHit,
    MemberPage,
    RiskBand,
    SegmentCard,
)

router = APIRouter()
manager_up = [Depends(require_role("manager", "admin"))]


def filters(
    segment: str | None = None,
    risk_band: RiskBand | None = None,
    club_id: str | None = None,
    min_tenure: Annotated[int | None, Query(ge=0)] = None,
    max_tenure: Annotated[int | None, Query(ge=0)] = None,
    q: str | None = None,
) -> dict:
    return {
        "segment": segment,
        "risk": risk_band,
        "club": club_id,
        "min_tenure": min_tenure,
        "max_tenure": max_tenure,
        "q": q,
    }


Filters = Annotated[dict, Depends(filters)]
Order = Literal["asc", "desc"]


def _data_or_503(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.DataNotBuilt as e:
        raise HTTPException(503, str(e)) from None


@router.get("", response_model=MemberPage, dependencies=manager_up)
def list_members(
    f: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 25,
    sort: str = "churn_prob",
    order: Order = "desc",
):
    return _data_or_503(service.list_members, page, page_size, sort, order, **f)


@router.get("/export.csv", response_class=PlainTextResponse, dependencies=manager_up)
def export_members(f: Filters, sort: str = "churn_prob", order: Order = "desc"):
    csv = _data_or_503(service.export_csv, sort, order, **f)
    headers = {"Content-Disposition": 'attachment; filename="members.csv"'}
    return PlainTextResponse(csv, media_type="text/csv", headers=headers)


@router.get("/facets", response_model=Facets, dependencies=manager_up)
def facets():
    return _data_or_503(service.facets)


@router.get("/search", response_model=list[MemberHit])
def search(q: Annotated[str, Query(min_length=1)], limit: Annotated[int, Query(le=50)] = 10):
    return _data_or_503(service.search, q, limit)


@router.get("/segments", response_model=list[SegmentCard], dependencies=manager_up)
def segments():
    return _data_or_503(service.segment_cards)


@router.get("/dashboard", response_model=Dashboard, dependencies=manager_up)
def dashboard(session: SessionDep):
    return _data_or_503(service.dashboard, session)


@router.get("/{member_id}", response_model=MemberDetail)
def member_detail(member_id: str):
    detail = _data_or_503(service.member_detail, member_id)
    if detail is None:
        raise HTTPException(404, f"Unknown member {member_id}")
    return detail
