"""
Real auth dependency, replacing the earlier X-User-Id header stub now that
app/routers/auth.py exists. Decodes a Bearer JWT and loads the user from
Postgres.

Pantry/Favorites routers depend on `get_current_user_id`, which is kept as
a thin wrapper over `get_current_user` so those routers didn't need to
change when this was swapped in.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="No such user")
    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.id


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Same decode as get_current_user, but returns None instead of 401 when
    there's no/invalid token -- for endpoints that work anonymously (e.g.
    ML-01 recommendations) but personalise when a valid token is present."""
    if credentials is None:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Gate for /api/admin/* routes -- 403s anyone whose role isn't 'admin'.
    Role is re-checked against the DB on every call (via get_current_user),
    not cached in the JWT, so a promotion/demotion takes effect immediately."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
