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

from app.algorithm.constraints import BLOCKED_SLOTS, ONLINE_PERIOD
from app.algorithm.engine import (
    CourseInput,
    InfeasibleModelError,
    RoomInput,
    SlotAssignment,
    SolverTimeoutError,
    solve,
)
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
TASK_INFEASIBLE = "INFEASIBLE"   # 제약조건상 시간표가 존재하지 않음
TASK_TIMEOUT = "TIMEOUT"         # 해가 존재할 수 있으나 제한 시간 내에 못 찾음
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
) -> list[CourseInput]:
    courses = db.query(Course).all()
    result = []
    for c in courses:
        result.append(
            CourseInput(
                id=c.id,
                course_name=c.course_name,
                professor_id=c.professor_id,
                department=c.department,
                target_grade=c.target_grade,
                weekly_hours=c.weekly_hours,
                online_hours=getattr(c, "online_hours", 0) or 0,
                expected_students=c.expected_students,
                requires_computer=c.requires_computer,
                non_preferred_days=c.non_preferred_days or [],
                non_preferred_periods=c.non_preferred_periods or [],
                preferred_days=c.preferred_days or [],
                preferred_periods=c.preferred_periods or [],
                fixed_room_ids=c.fixed_room_ids or [],
                unavailable_room_ids=c.unavailable_room_ids or [],
                block_preference=c.block_preference,
                mutually_exclusive_with=c.mutually_exclusive_with,
                fixed_schedules=c.fixed_schedules,
                target_cohorts=c.target_cohorts,
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
        )
        for r in rooms
    ]


def _persist_results(
    db: Session,
    task_id: str,
    results: list,
) -> list[Timetable]:
    """Save algorithm results to DB as CANDIDATE timetables."""
    saved = []
    for rank, result in enumerate(results, start=1):
        tt = Timetable(
            name=f"추천안 {rank}",
            status="CANDIDATE",
            version=1,
            score=result.score,
            pref_rate=result.pref_rate,
            fitness_rate=result.fitness_rate,
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
    min_candidates: int,
    fixed_assignment_ids: list[int] = None,
) -> None:
    """
    Run the generation algorithm in a thread pool executor so the
    FastAPI event loop is not blocked by OR-Tools CPU work.
    """
    loop = asyncio.get_event_loop()

    def _worker():
        db: Session = db_factory()
        try:
            course_inputs = _build_course_inputs(db)
            room_inputs = _build_room_inputs(db)
            
            fixed_slots = None
            if fixed_assignment_ids:
                from app.models.timetable import Assignment
                assignments = db.query(Assignment).filter(Assignment.id.in_(fixed_assignment_ids)).all()
                fixed_slots = [
                    {
                        "course_id": a.course_id,
                        "day": a.day,
                        "start_period": a.start_period,
                        "room_id": a.room_id
                    }
                    for a in assignments
                ]

            if not course_inputs:
                _tasks[task_id]["status"] = TASK_INFEASIBLE
                _tasks[task_id]["error"] = "제약조건을 모두 만족하는 시간표 생성 불가"
                return

            try:
                results = solve(
                    course_inputs,
                    room_inputs,
                    fixed_slots=fixed_slots,
                    min_candidates=min_candidates,
                    timeout_seconds=settings.algorithm_timeout_seconds,
                )
            except InfeasibleModelError as exc:
                _tasks[task_id]["status"] = TASK_INFEASIBLE
                _tasks[task_id]["error"] = str(exc)
                return
            except SolverTimeoutError as exc:
                # 제약조건 문제가 아니라 계산 시간 문제 — 구분해서 알려야 사용자가
                # 멀쩡한 제약조건을 헛되이 뜯어고치지 않는다.
                _tasks[task_id]["status"] = TASK_TIMEOUT
                _tasks[task_id]["error"] = str(exc)
                return

            if not results:
                _tasks[task_id]["status"] = TASK_INFEASIBLE
                _tasks[task_id]["error"] = "제약조건을 모두 만족하는 시간표 생성 불가"
                return

            saved = _persist_results(db, task_id, results)
            _tasks[task_id]["status"] = TASK_COMPLETED
            _tasks[task_id]["candidates"] = [t.id for t in saved]

        except Exception as exc:
            _tasks[task_id]["status"] = TASK_FAILED
            _tasks[task_id]["error"] = str(exc)
        finally:
            db.close()

    await loop.run_in_executor(_executor, _worker)


# ── Candidate queries ──────────────────────────────────────────────────────────

def list_candidates(db: Session) -> list[Timetable]:
    return (
        db.query(Timetable)
        .filter(Timetable.status == "CANDIDATE")
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
    target_room_id: int | None,
    target_day: str,
    target_period: int,
    ignore_assignment_id: int = None,
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
    room = db.query(Room).filter(Room.id == target_room_id).first() if target_room_id else None
    professor = db.query(Professor).filter(Professor.id == course.professor_id).first()

    # 0교시는 온라인 전용 — 강의실을 지정한 대면 배정은 놓을 수 없다.
    if target_period == ONLINE_PERIOD and target_room_id is not None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-11",
                    "message": "0교시는 온라인 수업 전용이라 강의실을 배정할 수 없습니다."},
        )
    if target_period != ONLINE_PERIOD and target_room_id is None:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-12",
                    "message": "대면 수업(1~9교시)에는 강의실을 지정해야 합니다."},
        )

    # Slots the engine never uses (e.g. WED 5–6교시 공동시간)
    if (target_day, target_period) in BLOCKED_SLOTS:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-06", "message": "해당 시간대는 배정이 불가능한 공동 시간입니다."},
        )

    # HC-03 불가 요일
    if target_day in (course.non_preferred_days or []):
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-07", "message": f"'{course.course_name}'의 불가 요일({target_day})입니다."},
        )

    # HC-04 불가 교시
    if target_period in (course.non_preferred_periods or []):
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-08", "message": f"'{course.course_name}'의 불가 교시({target_period}교시)입니다."},
        )

    # HC-05 고정 강의실 / HC-06 배정 불가 강의실
    if course.fixed_room_ids and target_room_id not in course.fixed_room_ids:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-09", "message": "해당 강의는 지정된 고정 강의실만 사용할 수 있습니다."},
        )
    if target_room_id in (course.unavailable_room_ids or []):
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-10", "message": "배정 불가로 지정된 강의실입니다."},
        )

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
    rq = db.query(Assignment).filter(
        Assignment.timetable_id == timetable_id,
        Assignment.id != assignment_id,
        Assignment.room_id == target_room_id,
        Assignment.day == target_day,
        Assignment.start_period == target_period,
    )
    if ignore_assignment_id:
        rq = rq.filter(Assignment.id != ignore_assignment_id)
    room_conflict = rq.first()
    if room_conflict:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-02", "message": "강의실 중복 배정이 발생했습니다."},
        )

    # HC-02 professor double-booking
    oq = db.query(Assignment.course_id).filter(
        Assignment.timetable_id == timetable_id,
        Assignment.id != assignment_id,
        Assignment.day == target_day,
        Assignment.start_period == target_period,
    )
    if ignore_assignment_id:
        oq = oq.filter(Assignment.id != ignore_assignment_id)
    other_course_ids = oq.subquery()
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

    # HC-10 cohort (same student group) double-booking — enforced by the engine,
    # so the manual editor must enforce it too.
    cohorts = set(course.target_cohorts or [f"{course.department}_{course.target_grade}"])
    other_courses = (
        db.query(Course).filter(Course.id.in_(other_course_ids)).all()
    )
    for other in other_courses:
        other_cohorts = set(
            other.target_cohorts or [f"{other.department}_{other.target_grade}"]
        )
        if cohorts & other_cohorts:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "ER-05",
                    "message": f"동일 수강 대상({', '.join(sorted(cohorts & other_cohorts))})의 "
                               f"'{other.course_name}' 수업과 시간이 겹칩니다.",
                },
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
    type: str,
    target_name: str | None = None,
) -> dict:
    """
    Get a structured view of CONFIRMED timetables.
    type: "room" | "professor" | "grade" | "department"
    """
    confirmed = (
        db.query(Timetable)
        .filter(Timetable.status == "CONFIRMED")
        .all()
    )
    if not confirmed:
        return []

    tt_ids = [t.id for t in confirmed]
    assignments = (
        db.query(Assignment).filter(Assignment.timetable_id.in_(tt_ids)).all()
    )

    result = []
    for a in assignments:
        course = db.query(Course).filter(Course.id == a.course_id).first()
        room = db.query(Room).filter(Room.id == a.room_id).first() if a.room_id else None
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

        if type == "room" and target_name and room:
            if room.room_name != target_name:
                continue
        elif type == "professor" and target_name and prof:
            if prof.name != target_name:
                continue
        elif type == "grade" and target_name and course:
            if str(course.target_grade) != target_name:
                continue
        elif type == "department" and target_name and course:
            if course.department != target_name:
                continue

        result.append(row)

    return result


def validate_swap(db: Session, timetable_id: int, assignment1_id: int, assignment2_id: int) -> dict:
    a1 = db.query(Assignment).filter(Assignment.id == assignment1_id, Assignment.timetable_id == timetable_id).first()
    a2 = db.query(Assignment).filter(Assignment.id == assignment2_id, Assignment.timetable_id == timetable_id).first()
    if not a1 or not a2:
        raise HTTPException(status_code=404, detail="해당 배정을 찾을 수 없습니다.")

    validate_move(db, timetable_id, assignment1_id, a2.room_id, a2.day, a2.start_period, ignore_assignment_id=assignment2_id)
    validate_move(db, timetable_id, assignment2_id, a1.room_id, a1.day, a1.start_period, ignore_assignment_id=assignment1_id)
    return {"ok": True}
