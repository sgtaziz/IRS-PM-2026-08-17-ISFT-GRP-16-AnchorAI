from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from anchorai.auth.security import decode_access_token
from anchorai.db.models import ROLES, User
from anchorai.db.session import get_session

ANY_ROLE = ROLES

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    if creds is None:
        raise _unauthorized("Not authenticated")
    try:
        claims = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token") from None
    # Load the row so deactivation and role changes apply before the token expires.
    uid = claims["uid"]
    user = session.get(User, uid) if isinstance(uid, int) else None
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[..., User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return dependency
