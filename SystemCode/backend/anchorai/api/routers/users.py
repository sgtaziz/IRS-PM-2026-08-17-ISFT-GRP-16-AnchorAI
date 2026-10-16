from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from anchorai.api.deps import SessionDep, require_role
from anchorai.auth import users
from anchorai.auth.users import PasswordReset, UserCreate, UserRow, UserUpdate
from anchorai.db.models import User

router = APIRouter()
Admin = Annotated[User, Depends(require_role("admin"))]


@router.get("", response_model=list[UserRow])
def list_users(session: SessionDep):
    return users.list_users(session)


@router.post("", response_model=UserRow, status_code=201)
def create_user(body: UserCreate, session: SessionDep, actor: Admin):
    try:
        return users.create_user(session, actor, body)
    except users.UserConflict as e:
        raise HTTPException(409, str(e)) from None


@router.patch("/{user_id}", response_model=UserRow)
def update_user(user_id: int, body: UserUpdate, session: SessionDep, actor: Admin):
    try:
        return users.update_user(session, actor, user_id, body)
    except users.UnknownUser as e:
        raise HTTPException(404, str(e)) from None
    except users.UserRuleViolation as e:
        raise HTTPException(409, str(e)) from None


@router.post("/{user_id}/password", status_code=204)
def reset_password(user_id: int, body: PasswordReset, session: SessionDep, actor: Admin):
    try:
        users.reset_password(session, actor, user_id, body)
    except users.UnknownUser as e:
        raise HTTPException(404, str(e)) from None
