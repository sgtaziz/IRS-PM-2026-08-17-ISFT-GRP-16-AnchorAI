from fastapi import APIRouter, Depends

from anchorai.api.deps import require_role
from anchorai.config import get_settings

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    # Public liveness check: no configuration, since the LLM endpoint is private.
    return {"status": "ok"}


@router.get("/api/health/details", dependencies=[Depends(require_role("admin"))])
def health_details() -> dict:
    s = get_settings()
    return {"status": "ok", "llm_base_url": s.llm_base_url, "llm_model": s.llm_model}
