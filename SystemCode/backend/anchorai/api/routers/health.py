from fastapi import APIRouter

from anchorai.config import get_settings

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm_base_url": s.llm_base_url, "llm_model": s.llm_model}
