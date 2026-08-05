from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.timetable import Timetable, Assignment
from app.schemas.course import CourseCreate, CourseUpdate


def list_courses(db: Session) -> list[Course]:
    return db.query(Course).all()


def get_course(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="해당 강의를 찾을 수 없습니다.")
    return course


def create_course(db: Session, data: CourseCreate) -> Course:
    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course_id: int, data: CourseUpdate) -> Course:
    course = get_course(db, course_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, course_id: int) -> None:
    course = get_course(db, course_id)
    db.delete(course)
    db.commit()


def reset_all_courses(db: Session) -> None:
    db.query(Assignment).delete()
    db.query(Timetable).delete()
    db.query(Course).delete()
    db.commit()
