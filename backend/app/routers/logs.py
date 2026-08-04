from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.log import Log
from app.response import success_response

router = APIRouter(prefix="/api/v1/logs", tags=["이력 관리"])


@router.get("")
def list_logs(
    semester_id: int | None = None,
    log_type: str | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """이력 로그 목록 조회."""
    query = db.query(Log)
    if log_type:
        query = query.filter(Log.log_type == log_type.upper())
    logs = query.order_by(Log.created_at.desc()).limit(500).all()

    data = [
        {
            "id": log.id,
            "log_type": log.log_type,
            "username": log.username,
            "detail": log.detail,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
    return success_response(data=data)
