from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from anchorai.api.deps import CurrentUser, SessionDep
from anchorai.auth.schemas import LoginRequest, TokenResponse, UserOut
from anchorai.auth.security import burn_password_check, create_access_token, verify_password
from anchorai.db.audit import record_audit
from anchorai.db.models import User

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, session: SessionDep) -> TokenResponse:
    user = session.exec(select(User).where(User.username == req.username)).first()
    if user is None or not user.is_active:
        burn_password_check(req.password)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    record_audit(session, user, "login", "user", str(user.id))
    session.commit()
    return TokenResponse(
        access_token=create_access_token(user), user=UserOut.model_validate(user.model_dump())
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user.model_dump())
