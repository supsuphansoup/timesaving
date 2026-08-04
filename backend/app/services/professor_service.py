from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.professor import Professor
from app.schemas.professor import ProfessorCreate, ProfessorUpdate


def list_professors(db: Session, semester_id: int) -> list[Professor]:
    return db.query(Professor).filter(Professor.semester_id == semester_id).all()


def get_professor(db: Session, professor_id: int) -> Professor:
    prof = db.query(Professor).filter(Professor.id == professor_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="해당 교수를 찾을 수 없습니다.")
    return prof


def create_professor(db: Session, data: ProfessorCreate) -> Professor:
    # ER-08: duplicate check
    existing = (
        db.query(Professor)
        .filter(Professor.name == data.name, Professor.semester_id == data.semester_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-08", "message": "중복된 데이터가 존재합니다."},
        )
    prof = Professor(**data.model_dump())
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof


def update_professor(db: Session, professor_id: int, data: ProfessorUpdate) -> Professor:
    prof = get_professor(db, professor_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prof, field, value)
    db.commit()
    db.refresh(prof)
    return prof


def delete_professor(db: Session, professor_id: int) -> None:
    prof = get_professor(db, professor_id)
    db.delete(prof)
    db.commit()
