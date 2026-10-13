from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from anchorai.api.routers import assistant, health, members, plan, rules

app = FastAPI(title="AnchorAI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(members.router, prefix="/api/members", tags=["members (Stream A)"])
app.include_router(plan.router, prefix="/api/plan", tags=["plan (Stream B)"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules (Stream C)"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant (Stream C)"])
