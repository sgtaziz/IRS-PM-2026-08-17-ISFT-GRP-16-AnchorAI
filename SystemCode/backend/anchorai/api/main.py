from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anchorai.api.deps import ANY_ROLE, require_role
from anchorai.api.routers import assistant, auth, health, members, plan, rules

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
