from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Course, Professor, Room, AuditLog, User
from ..schemas import CourseCreate, CourseUpdate, CourseResponse
from .auth import get_current_user

router = APIRouter(prefix="/api/courses", tags=["courses"])

def course_to_response(c: Course, db: Session) -> dict:
    prof = db.query(Professor).filter(Professor.id == c.professor_id).first()
    room = db.query(Room).filter(Room.id == c.fixed_room_id).first() if c.fixed_room_id else None
    return {
        "id": c.id,
        "semester_id": c.semester_id,
        "name": c.name,
        "professor_id": c.professor_id,
        "department": c.department,
        "grade": c.grade,
        "section": c.section,
        "weekly_hours": c.weekly_hours,
        "expected_students": c.expected_students,
        "computer_required": c.computer_required,
        "fixed_room_id": c.fixed_room_id,
        "professor_name": prof.name if prof else "미지정",
        "fixed_room_name": room.name if room else None
    }

@router.get("", response_model=List[CourseResponse])
def list_courses(
    semester_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    courses = db.query(Course).filter(Course.semester_id == semester_id).all()
    return [course_to_response(c, db) for c in courses]

@router.post("", response_model=CourseResponse)
def create_course(
    req: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = Course(
        semester_id=req.semester_id,
        name=req.name,
        professor_id=req.professor_id,
        department=req.department,
        grade=req.grade,
        section=req.section,
        weekly_hours=req.weekly_hours,
        expected_students=req.expected_students,
        computer_required=req.computer_required,
        fixed_room_id=req.fixed_room_id
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의 정보 신규 등록 ({course.name} - {course.department} {course.grade}학년 {course.section}반)"
    )
    db.add(log)
    db.commit()

    return course_to_response(course, db)

@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    req: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="강의 정보를 찾을 수 없습니다.")

    course.name = req.name
    course.professor_id = req.professor_id
    course.department = req.department
    course.grade = req.grade
    course.section = req.section
    course.weekly_hours = req.weekly_hours
    course.expected_students = req.expected_students
    course.computer_required = req.computer_required
    course.fixed_room_id = req.fixed_room_id

    db.commit()
    db.refresh(course)

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의 정보 수정 ({course.name})"
    )
    db.add(log)
    db.commit()

    return course_to_response(course, db)

@router.delete("/{course_id}", response_model=dict)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="강의 정보를 찾을 수 없습니다.")

    name = course.name
    db.delete(course)
    db.commit()

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의 삭제 ({name})"
    )
    db.add(log)
    db.commit()

    return {"message": f"{name} 강의 정보가 삭제되었습니다."}
