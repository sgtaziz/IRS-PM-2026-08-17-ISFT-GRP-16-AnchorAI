from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from anchorai.api.deps import SessionDep, require_role
from anchorai.config import get_settings
from anchorai.db.audit import record_audit
from anchorai.db.models import User
from anchorai.discovery import jobs
from anchorai.discovery.scores import load_model_card
from anchorai.scenario.build import SchemaError

router = APIRouter()
Admin = Annotated[User, Depends(require_role("admin"))]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class RebuildRequest(BaseModel):
    seed: int | None = None


@router.get("")
def overview() -> dict:
    try:
        card = load_model_card()
    except FileNotFoundError:
        card = {}
    return {**card, "build": jobs.status(), "raw": jobs.raw_info()}


@router.post("/upload")
async def upload(request: Request, session: SessionDep, user: Admin) -> dict:
    """Body is the raw CSV (Content-Type text/csv)."""
    content = await request.body()
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "Send the Kaggle CSV as the request body (max 20 MB)")
    try:
        rows = jobs.replace_raw(content)
    except (SchemaError, ValueError) as e:
        raise HTTPException(422, str(e)) from None
    record_audit(session, user, "data.upload", "raw_data", jobs.RAW_NAME, None, {"rows": rows})
    session.commit()
    return {"rows": rows, "raw": jobs.raw_info()}


@router.post("/rebuild", status_code=202)
def rebuild(req: RebuildRequest, session: SessionDep, user: Admin) -> dict:
    seed = get_settings().anchorai_seed if req.seed is None else req.seed
    try:
        state = jobs.start_rebuild(seed)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from None
    record_audit(session, user, "data.rebuild", "data", None, None, {"seed": seed})
    session.commit()
    return state
