from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
def list_members(segment: str | None = None, min_risk: float = 0.0, limit: int = 100):
    raise HTTPException(501, "TODO Stream A: return MemberScore rows, filterable")


@router.get("/segments")
def segments():
    raise HTTPException(501, "TODO Stream A: segment names, sizes, centroid profiles, churn rate")


@router.get("/{member_id}")
def member_detail(member_id: str):
    raise HTTPException(501, "TODO Stream A: MemberScore + visit history for charts")
