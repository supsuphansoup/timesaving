"""
Session-based authentication dependency.

Sessions are stored in a module-level dict (in-memory) keyed by session_id.
The session_id is placed in an httponly signed cookie using itsdangerous.
"""

import uuid
from typing import Optional

from fastapi import Cookie, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

# In-memory session store: { session_id -> {user_id, username} }
_sessions: dict[str, dict] = {}

_signer = URLSafeTimedSerializer(settings.secret_key)


def create_session(user_id: int, username: str) -> str:
    """Create a new session and return the signed session token to be set as cookie."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"user_id": user_id, "username": username}
    token = _signer.dumps(session_id, salt="session")
    return token


def destroy_session(token: str) -> None:
    """Invalidate a session by its signed token."""
    try:
        session_id = _signer.loads(token, salt="session", max_age=settings.session_max_age)
        _sessions.pop(session_id, None)
    except Exception:
        pass


def get_current_user(session: Optional[str] = Cookie(default=None)) -> dict:
    """
    FastAPI dependency that reads the signed session cookie and returns
    {user_id, username}. Raises HTTP 401 if unauthenticated.
    """
    if not session:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "status_code": 401, "error_code": "ER-06", "message": "권한이 없습니다. 로그인이 필요합니다."},
        )
    try:
        session_id = _signer.loads(session, salt="session", max_age=settings.session_max_age)
    except (SignatureExpired, BadSignature):
        raise HTTPException(
            status_code=401,
            detail={"success": False, "status_code": 401, "error_code": "ER-06", "message": "세션이 만료되었습니다. 다시 로그인해 주세요."},
        )

    user_data = _sessions.get(session_id)
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "status_code": 401, "error_code": "ER-06", "message": "세션이 유효하지 않습니다. 다시 로그인해 주세요."},
        )
    return user_data
