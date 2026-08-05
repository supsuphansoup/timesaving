from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.log import Log
from app.response import success_response
from app.schemas.professor import ProfessorCreate, ProfessorOut, ProfessorUpdate
from app.services import professor_service

router = APIRouter(prefix="/api/v1/professors", tags=["교수 관리"])


@router.get("")
def list_professors(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    professors = professor_service.list_professors(db)
    return success_response(data=[ProfessorOut.model_validate(p).model_dump() for p in professors])


@router.post("")
def create_professor(
    body: ProfessorCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prof = professor_service.create_professor(db, body)
    db.add(Log(log_type="MODIFY", user_id=current_user["user_id"], username=current_user["username"], detail={"action": "create_professor", "professor_id": prof.id}))
    db.commit()
    return success_response(data=ProfessorOut.model_validate(prof).model_dump(), status_code=201)


@router.put("/{professor_id}")
def update_professor(
    professor_id: int,
    body: ProfessorUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prof = professor_service.update_professor(db, professor_id, body)
    db.add(Log(log_type="MODIFY", user_id=current_user["user_id"], username=current_user["username"], detail={"action": "update_professor", "professor_id": professor_id}))
    db.commit()
    return success_response(data=ProfessorOut.model_validate(prof).model_dump())


@router.delete("/{professor_id}")
def delete_professor(
    professor_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    professor_service.delete_professor(db, professor_id)
    return success_response(message="교수 정보가 삭제되었습니다.")
