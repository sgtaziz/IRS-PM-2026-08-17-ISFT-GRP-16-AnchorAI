from fastapi import APIRouter, Depends

from anchorai import health as system
from anchorai.api.deps import SessionDep, require_role

router = APIRouter()
admin = [Depends(require_role("admin"))]


@router.get("/api/health")
def health() -> dict:
    # Public liveness check: no configuration, since the LLM endpoint is private.
    return {"status": "ok"}


@router.get("/api/health/details", dependencies=admin)
def health_details(session: SessionDep) -> dict:
    return system.details(session)


@router.post("/api/health/llm-test", dependencies=admin)
def test_llm() -> dict:
    return system.test_llm()
