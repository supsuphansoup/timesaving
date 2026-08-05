from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.response import success_response
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate
from app.services import course_service

router = APIRouter(prefix="/api/v1/courses", tags=["강의 관리"])


@router.get("")
def list_courses(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    courses = course_service.list_courses(db)
    return success_response(data=[CourseOut.model_validate(c).model_dump() for c in courses])


@router.post("")
def create_course(
    body: CourseCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    course = course_service.create_course(db, body)
    return success_response(data=CourseOut.model_validate(course).model_dump(), status_code=201)


@router.put("/{course_id}")
def update_course(
    course_id: int,
    body: CourseUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    course = course_service.update_course(db, course_id, body)
    return success_response(data=CourseOut.model_validate(course).model_dump())


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    course_service.delete_course(db, course_id)
    return success_response(message="강의 정보가 삭제되었습니다.")


@router.delete("/action/reset")
def reset_courses(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    course_service.reset_all_courses(db)
    return success_response(message="모든 강의 및 시간표 정보가 초기화되었습니다.")
