import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Professor, AuditLog, User
from ..schemas import ProfessorCreate, ProfessorUpdate, ProfessorResponse
from .auth import get_current_user

router = APIRouter(prefix="/api/professors", tags=["professors"])

def prof_to_response(p: Professor) -> dict:
    return {
        "id": p.id,
        "semester_id": p.semester_id,
        "name": p.name,
        "department": p.department,
        "phone": p.phone,
        "email": p.email,
        "unavailable_days": json.loads(getattr(p, "unavailable_days", "[]") or "[]"),
        "preferred_days": json.loads(getattr(p, "preferred_days", "[]") or "[]"),
        "unavailable_periods": json.loads(getattr(p, "unavailable_periods", "[]") or "[]"),
        "preferred_periods": json.loads(getattr(p, "preferred_periods", "[]") or "[]"),
        "unavailable_slots": json.loads(getattr(p, "unavailable_slots", "[]") or "[]"),
        "preferred_slots": json.loads(getattr(p, "preferred_slots", "[]") or "[]"),
        "fixed_room_id": p.fixed_room_id,
        "unavailable_room_ids": json.loads(getattr(p, "unavailable_room_ids", "[]") or "[]"),
        "weekly_hours_limit": p.weekly_hours_limit
    }

@router.get("", response_model=List[ProfessorResponse])
def list_professors(
    semester_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profs = db.query(Professor).filter(Professor.semester_id == semester_id).all()
    return [prof_to_response(p) for p in profs]

@router.post("", response_model=ProfessorResponse)
def create_professor(
    req: ProfessorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prof = Professor(
        semester_id=req.semester_id,
        name=req.name,
        department=req.department,
        phone=req.phone,
        email=req.email,
        unavailable_days=json.dumps(req.unavailable_days),
        preferred_days=json.dumps(req.preferred_days),
        unavailable_periods=json.dumps(req.unavailable_periods),
        preferred_periods=json.dumps(req.preferred_periods),
        unavailable_slots=json.dumps(req.unavailable_slots),
        preferred_slots=json.dumps(req.preferred_slots),
        fixed_room_id=req.fixed_room_id,
        unavailable_room_ids=json.dumps(req.unavailable_room_ids),
        weekly_hours_limit=req.weekly_hours_limit
    )
    db.add(prof)
    db.commit()
    db.refresh(prof)

    # Audit log
    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"교수 정보 및 제약조건 신규 등록 ({prof.name} 교수)"
    )
    db.add(log)
    db.commit()

    return prof_to_response(prof)

@router.put("/{prof_id}", response_model=ProfessorResponse)
def update_professor(
    prof_id: int,
    req: ProfessorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prof = db.query(Professor).filter(Professor.id == prof_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="교수 정보를 찾을 수 없습니다.")

    prof.name = req.name
    prof.department = req.department
    prof.phone = req.phone
    prof.email = req.email
    prof.unavailable_days = json.dumps(req.unavailable_days)
    prof.preferred_days = json.dumps(req.preferred_days)
    prof.unavailable_periods = json.dumps(req.unavailable_periods)
    prof.preferred_periods = json.dumps(req.preferred_periods)
    prof.unavailable_slots = json.dumps(req.unavailable_slots)
    prof.preferred_slots = json.dumps(req.preferred_slots)
    prof.fixed_room_id = req.fixed_room_id
    prof.unavailable_room_ids = json.dumps(req.unavailable_room_ids)
    prof.weekly_hours_limit = req.weekly_hours_limit

    db.commit()
    db.refresh(prof)

    # Audit log
    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"교수 제약조건 수정 완료 ({prof.name} 교수)"
    )
    db.add(log)
    db.commit()

    return prof_to_response(prof)

@router.delete("/{prof_id}", response_model=dict)
def delete_professor(
    prof_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prof = db.query(Professor).filter(Professor.id == prof_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="교수 정보를 찾을 수 없습니다.")

    name = prof.name
    db.delete(prof)
    db.commit()

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"교수 정보 삭제 ({name} 교수)"
    )
    db.add(log)
    db.commit()

    return {"message": f"{name} 교수 정보가 삭제되었습니다."}
