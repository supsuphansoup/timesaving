from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.semester import Semester
from app.response import success_response, error_response
from pydantic import BaseModel, Field


class SemesterCreate(BaseModel):
    name: str = Field(..., min_length=1)
    year: int = Field(..., ge=2000, le=2100)
    term: int = Field(..., ge=1, le=4)
    is_active: bool = True


router = APIRouter(prefix="/api/v1/semesters", tags=["학기 관리"])


@router.get("")
def list_semesters(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    semesters = db.query(Semester).order_by(Semester.id.desc()).all()
    data = [
        {
            "id": s.id,
            "name": s.name,
            "year": s.year,
            "term": s.term,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat(),
        }
        for s in semesters
    ]
    return success_response(data=data)


@router.post("", status_code=201)
def create_semester(
    body: SemesterCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    # Check duplicate
    existing = db.query(Semester).filter(
        Semester.year == body.year,
        Semester.term == body.term,
    ).first()
    if existing:
        return error_response("이미 동일한 학기가 존재합니다.", "ER-08", 409)

    sem = Semester(**body.model_dump())
    db.add(sem)
    db.commit()
    db.refresh(sem)
    return success_response(
        data={"id": sem.id, "name": sem.name, "year": sem.year, "term": sem.term},
        status_code=201,
    )


@router.delete("/{semester_id}")
def delete_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    sem = db.query(Semester).filter(Semester.id == semester_id).first()
    if not sem:
        return error_response("해당 학기를 찾을 수 없습니다.", "ER-07", 404)
    db.delete(sem)
    db.commit()
    return success_response(message="학기가 삭제되었습니다.")
