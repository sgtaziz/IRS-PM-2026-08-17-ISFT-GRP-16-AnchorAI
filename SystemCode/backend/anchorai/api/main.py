import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anchorai.api.deps import ANY_ROLE, require_role
from anchorai.api.routers import assistant, auth, health, members, plan, rules
from anchorai.config import INSECURE_JWT_SECRETS, get_settings

if get_settings().anchorai_jwt_secret in INSECURE_JWT_SECRETS:
    logging.getLogger("uvicorn.error").warning(
        "ANCHORAI_JWT_SECRET is a published default; set a random one in .env "
        "(openssl rand -hex 32) before sharing this server."
    )

app = FastAPI(title="AnchorAI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

any_role = [Depends(require_role(*ANY_ROLE))]
manager_up = [Depends(require_role("manager", "admin"))]

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
    assistant.router, prefix="/api/assistant", tags=["assistant (Stream C)"], dependencies=any_role
)
