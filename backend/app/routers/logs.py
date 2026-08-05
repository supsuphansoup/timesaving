from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, User
from ..schemas import AuditLogResponse
from .auth import get_current_user

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("", response_model=List[AuditLogResponse])
def get_logs(
    category: Optional[str] = Query(None, description="LOGIN, GENERATE, UPDATE, CONFIRM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AuditLog)
    if category and category != "ALL":
        query = query.filter(AuditLog.category == category)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return logs
