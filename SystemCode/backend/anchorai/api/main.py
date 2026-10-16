import logging
import sys
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anchorai.api.deps import ANY_ROLE, require_role
from anchorai.api.routers import (
    admin_audit,
    admin_data,
    admin_gym,
    admin_kg,
    admin_offers,
    assistant,
    auth,
    drafts,
    graph,
    health,
    members,
    plan,
    rules,
    users,
)
from anchorai.config import INSECURE_JWT_SECRETS, get_settings

if get_settings().anchorai_jwt_secret in INSECURE_JWT_SECRETS:
    logging.getLogger("uvicorn.error").warning(
        "ANCHORAI_JWT_SECRET is a published default; set a random one in .env "
        "(openssl rand -hex 32) before sharing this server."
    )


def _warm_up_assistant() -> None:
    from anchorai.assistant.classifier import get_classifier

    try:
        get_classifier()
    except Exception:
        logging.getLogger("uvicorn.error").exception("assistant warm-up failed")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Loading the embedding model takes seconds; do it now so the first question doesn't wait.
    if get_settings().assistant_warmup and "pytest" not in sys.modules:
        threading.Thread(target=_warm_up_assistant, name="assistant-warmup", daemon=True).start()
    yield


app = FastAPI(title="AnchorAI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

any_role = [Depends(require_role(*ANY_ROLE))]
manager_up = [Depends(require_role("manager", "admin"))]
admin_only = [Depends(require_role("admin"))]

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/auth", tags=["auth (Stream C)"])
app.include_router(
    members.router, prefix="/api/members", tags=["members (Stream A)"], dependencies=any_role
)
app.include_router(
    plan.router, prefix="/api/plan", tags=["plan (Stream B)"], dependencies=manager_up
)
app.include_router(
    rules.router, prefix="/api/rules", tags=["rules (Stream C)"], dependencies=any_role
)
app.include_router(
    graph.router, prefix="/api/graph", tags=["graph (Stream C)"], dependencies=any_role
)
app.include_router(
    assistant.router, prefix="/api/assistant", tags=["assistant (Stream C)"], dependencies=any_role
)
app.include_router(
    drafts.router, prefix="/api/drafts", tags=["drafts (Stream C)"], dependencies=any_role
)
app.include_router(
    admin_data.router,
    prefix="/api/admin/data",
    tags=["admin data (Stream A)"],
    dependencies=admin_only,
)
app.include_router(
    admin_offers.router,
    prefix="/api/admin/offers",
    tags=["admin offers (Stream A)"],
    dependencies=admin_only,
)
app.include_router(
    admin_audit.router,
    prefix="/api/admin/audit",
    tags=["admin audit (Stream C)"],
    dependencies=admin_only,
)
app.include_router(
    users.router,
    prefix="/api/admin/users",
    tags=["admin users (Stream C)"],
    dependencies=admin_only,
)
app.include_router(
    admin_gym.router,
    prefix="/api/admin/gym",
    tags=["admin gym (Stream C)"],
    dependencies=manager_up,
)
app.include_router(
    admin_kg.router,
    prefix="/api/admin/kg",
    tags=["admin kg (Stream C)"],
    dependencies=manager_up,
)
