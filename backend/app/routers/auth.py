from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import create_session, destroy_session, get_current_user
from app.models.log import Log
from app.response import error_response, success_response
from app.schemas.auth import LoginRequest, PasswordChangeRequest
from app.services.auth_service import authenticate_user, change_password

router = APIRouter(prefix="/api/v1/auth", tags=["인증"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """조교 로그인 — 세션 쿠키 발급."""
    user = authenticate_user(db, body.username, body.password)

    # Save login log
    log = Log(
        log_type="LOGIN",
        username=body.username,
        detail={"success": user is not None},
    )
    db.add(log)
    db.commit()

    if not user:
        return error_response("아이디 또는 비밀번호가 올바르지 않습니다.", "ER-06", 401)

    token = create_session(user.id, user.username)
    # IMPORTANT: set_cookie must be called on the *returned* response object.
    # If we inject Response and call set_cookie on it, FastAPI ignores those
    # mutations when the route returns a different Response subclass.
    resp = success_response(message="로그인에 성공했습니다.")
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_max_age,
    )
    return resp


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회 — 세션 유지 확인용."""
    return success_response(data={"user_id": current_user["user_id"], "username": current_user["username"]})


@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user),
    session: str | None = Cookie(default=None),
):
    """로그아웃 — 세션 삭제."""
    if session:
        destroy_session(session)
    resp = success_response(message="로그아웃되었습니다.")
    resp.delete_cookie("session")
    return resp


@router.put("/password")
def update_password(
    body: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """비밀번호 변경."""
    ok = change_password(db, current_user["user_id"], body.old_password, body.new_password)
    if not ok:
        return error_response("현재 비밀번호가 올바르지 않습니다.", "ER-07", 400)
    return success_response(message="비밀번호가 변경되었습니다.")
