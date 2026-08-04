"""
Timetable service — orchestrates algorithm execution, task tracking,
manual validation, partial reassignment, draft saving and confirmation.
"""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.algorithm.engine import CourseInput, RoomInput, SlotAssignment, solve
from app.config import settings
from app.models.course import Course
from app.models.professor import Professor
from app.models.room import Room
from app.models.timetable import Assignment, Timetable

# ── In-memory task store ───────────────────────────────────────────────────────
# Structure: {task_id: {status, candidates, error, created_at}}
_tasks: dict[str, dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=2)

TASK_PROCESSING = "PROCESSING"
TASK_COMPLETED = "COMPLETED"
TASK_INFEASIBLE = "INFEASIBLE"
TASK_FAILED = "FAILED"


# ── Task management ────────────────────────────────────────────────────────────

def create_task() -> str:
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "status": TASK_PROCESSING,
        "candidates": [],
        "error": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    return task_id


def get_task(task_id: str) -> dict:
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다.")
    return task


def _build_course_inputs(
    db: Session,
    semester_id: int,
) -> list[CourseInput]:
    courses = db.query(Course).filter(Course.semester_id == semester_id).all()
    result = []
    for c in courses:
        result.append(
            CourseInput(
                id=c.id,
                professor_id=c.professor_id,
                weekly_hours=c.weekly_hours,
                expected_students=c.expected_students,
                requires_computer=c.requires_computer,
                # Constraints now come from the Course, not the Professor
                unavailable_days=c.unavailable_days or [],
                unavailable_periods=c.unavailable_periods or [],
                preferred_days=c.preferred_days or [],
                preferred_periods=c.preferred_periods or [],
                fixed_room_ids=c.fixed_room_ids or [],
                unavailable_room_ids=c.unavailable_room_ids or [],
            )
        )
    return result


def _build_room_inputs(db: Session) -> list[RoomInput]:
    rooms = db.query(Room).all()
    return [
        RoomInput(
            id=r.id,
            capacity=r.capacity,
            is_computer_room=r.is_computer_room,
            unavailable_time=r.unavailable_time,
        )
        for r in rooms
    ]


def _persist_results(
    db: Session,
    task_id: str,
    semester_id: int,
    results: list,
) -> list[Timetable]:
    """Save algorithm results to DB as CANDIDATE timetables."""
    saved = []
    for rank, result in enumerate(results, start=1):
        tt = Timetable(
            semester_id=semester_id,
            name=f"추천안 {rank}",
            status="CANDIDATE",
            version=1,
            score=result.score,
            constraint_satisfaction_rate=result.constraint_satisfaction_rate,
            conflict_count=result.conflict_count,
            task_id=task_id,
            rank=rank,
        )
        db.add(tt)
        db.flush()  # get tt.id

        for slot in result.assignments:
            db.add(
                Assignment(
                    timetable_id=tt.id,
                    course_id=slot.course_id,
                    room_id=slot.room_id,
                    day=slot.day,
                    start_period=slot.start_period,
                    duration=slot.duration,
                )
            )
        saved.append(tt)
    db.commit()
    return saved


async def run_generation_async(
    db_factory,  # callable -> Session
    task_id: str,
    semester_id: int,
    min_candidates: int,
) -> None:
    """
    Run the generation algorithm in a thread pool executor so the
    FastAPI event loop is not blocked by OR-Tools CPU work.
    """
    loop = asyncio.get_event_loop()

    def _worker():
        db: Session = db_factory()
        try:
            course_inputs = _build_course_inputs(db, semester_id)
            room_inputs = _build_room_inputs(db)

            if not course_inputs:
                _tasks[task_id]["status"] = TASK_INFEASIBLE
                _tasks[task_id]["error"] = "제약조건을 모두 만족하는 시간표 생성 불가"
                return

            results = solve(
                course_inputs,
                room_inputs,
                min_candidates=min_candidates,
                timeout_seconds=settings.algorithm_timeout_seconds,
            )

            if not results:
                _tasks[task_id]["status"] = TASK_INFEASIBLE
                _tasks[task_id]["error"] = "제약조건을 모두 만족하는 시간표 생성 불가"
                return

            saved = _persist_results(db, task_id, semester_id, results)
            _tasks[task_id]["status"] = TASK_COMPLETED
            _tasks[task_id]["candidates"] = [t.id for t in saved]

        except Exception as exc:
            _tasks[task_id]["status"] = TASK_FAILED
            _tasks[task_id]["error"] = str(exc)
        finally:
            db.close()

    await loop.run_in_executor(_executor, _worker)


# ── Candidate queries ──────────────────────────────────────────────────────────

def list_candidates(db: Session, semester_id: int) -> list[Timetable]:
    return (
        db.query(Timetable)
        .filter(Timetable.semester_id == semester_id, Timetable.status == "CANDIDATE")
        .order_by(Timetable.rank)
        .all()
    )


def get_timetable(db: Session, timetable_id: int) -> Timetable:
    tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="해당 시간표를 찾을 수 없습니다.")
    return tt


def get_assignments(db: Session, timetable_id: int) -> list[Assignment]:
    return db.query(Assignment).filter(Assignment.timetable_id == timetable_id).all()


# ── Validate move ──────────────────────────────────────────────────────────────

def validate_move(
    db: Session,
    timetable_id: int,
    assignment_id: int,
    target_room_id: int,
    target_day: str,
    target_period: int,
) -> dict:
    """
    Check if moving an assignment to (target_room, target_day, target_period)
    causes any hard-constraint violation.
    Returns {"ok": True} or raises HTTPException with appropriate error code.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="해당 배정을 찾을 수 없습니다.")

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    room = db.query(Room).filter(Room.id == target_room_id).first()
    professor = db.query(Professor).filter(Professor.id == course.professor_id).first()

    # HC-08 capacity
    if room and room.capacity < course.expected_students:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-03", "message": "강의실 수용 인원이 부족합니다."},
        )

    # HC-07 computer room
    if course.requires_computer and room and not room.is_computer_room:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-04", "message": "사용 가능한 컴퓨터실이 없습니다."},
        )

    # HC-01 room double-booking
    room_conflict = (
        db.query(Assignment)
        .filter(
            Assignment.timetable_id == timetable_id,
            Assignment.id != assignment_id,
            Assignment.room_id == target_room_id,
            Assignment.day == target_day,
            Assignment.start_period == target_period,
        )
        .first()
    )
    if room_conflict:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-02", "message": "강의실 중복 배정이 발생했습니다."},
        )

    # HC-02 professor double-booking
    other_course_ids = (
        db.query(Assignment.course_id)
        .filter(
            Assignment.timetable_id == timetable_id,
            Assignment.id != assignment_id,
            Assignment.day == target_day,
            Assignment.start_period == target_period,
        )
        .subquery()
    )
    prof_conflict = (
        db.query(Course)
        .filter(
            Course.id.in_(other_course_ids),
            Course.professor_id == course.professor_id,
        )
        .first()
    )
    if prof_conflict:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-01", "message": "교수 시간 충돌이 발생했습니다."},
        )

    return {"ok": True}


# ── Draft save ─────────────────────────────────────────────────────────────────

def save_draft(
    db: Session,
    timetable_id: int,
    version: int,
    new_assignments: list[dict],
) -> Timetable:
    """Save a draft with Optimistic Locking."""
    tt = get_timetable(db, timetable_id)

    if tt.version != version:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-11", "message": "다른 사용자가 이미 이 시간표를 수정했습니다."},
        )

    # Delete existing assignments and replace
    db.query(Assignment).filter(Assignment.timetable_id == timetable_id).delete()
    for a in new_assignments:
        db.add(
            Assignment(
                timetable_id=timetable_id,
                course_id=a["course_id"],
                room_id=a["room_id"],
                day=a["day"],
                start_period=a["start_period"],
                duration=a.get("duration", 1),
            )
        )
    tt.status = "DRAFT"
    tt.version = version + 1
    db.commit()
    db.refresh(tt)
    return tt


# ── Confirm ────────────────────────────────────────────────────────────────────

def confirm_timetable(db: Session, timetable_id: int) -> Timetable:
    tt = get_timetable(db, timetable_id)
    tt.status = "CONFIRMED"
    db.commit()
    db.refresh(tt)
    return tt


# ── Views (filtered queries) ───────────────────────────────────────────────────

def get_timetable_view(
    db: Session,
    semester_id: int,
    view_type: str,
    target_name: str | None,
) -> list[dict]:
    """
    Return a list of assignment dicts filtered by view_type.
    view_type: room | professor | grade | department
    """
    timetables = (
        db.query(Timetable)
        .filter(Timetable.semester_id == semester_id, Timetable.status == "CONFIRMED")
        .all()
    )
    if not timetables:
        return []

    tt_ids = [t.id for t in timetables]
    assignments = (
        db.query(Assignment).filter(Assignment.timetable_id.in_(tt_ids)).all()
    )

    result = []
    for a in assignments:
        course = db.query(Course).filter(Course.id == a.course_id).first()
        room = db.query(Room).filter(Room.id == a.room_id).first()
        prof = db.query(Professor).filter(Professor.id == course.professor_id).first() if course else None

        row = {
            "assignment_id": a.id,
            "timetable_id": a.timetable_id,
            "day": a.day,
            "start_period": a.start_period,
            "duration": a.duration,
            "course_id": a.course_id,
            "course_name": course.course_name if course else None,
            "room_id": a.room_id,
            "room_name": room.room_name if room else None,
            "professor_id": course.professor_id if course else None,
            "professor_name": prof.name if prof else None,
            "department": course.department if course else None,
            "target_grade": course.target_grade if course else None,
        }

        if view_type == "room" and target_name and room:
            if room.room_name != target_name:
                continue
        elif view_type == "professor" and target_name and prof:
            if prof.name != target_name:
                continue
        elif view_type == "grade" and target_name and course:
            if str(course.target_grade) != target_name:
                continue
        elif view_type == "department" and target_name and course:
            if course.department != target_name:
                continue

        result.append(row)

    return result
