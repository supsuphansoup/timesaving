import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import (
    Course, Room, Professor, TimetableCandidate,
    TimetableAssignment, AuditLog, User
)
from ..schemas import (
    GenerateTimetableRequest, CandidateResponse, AssignmentResponse,
    ManualEditRequest, ValidationResult
)
from ..solver.scheduler import solve_timetable, validate_manual_edit
from .auth import get_current_user
from .professors import prof_to_response
from .rooms import room_to_response
from .courses import course_to_response

router = APIRouter(prefix="/api/timetables", tags=["timetables"])

def candidate_to_response(cand: TimetableCandidate, db: Session) -> dict:
    assignments_res = []
    assignments = db.query(TimetableAssignment).filter(TimetableAssignment.candidate_id == cand.id).all()

    for a in assignments:
        course = db.query(Course).filter(Course.id == a.course_id).first()
        room = db.query(Room).filter(Room.id == a.room_id).first()
        prof = db.query(Professor).filter(Professor.id == course.professor_id).first() if course else None

        assignments_res.append({
            "id": a.id,
            "course_id": a.course_id,
            "room_id": a.room_id,
            "day": a.day,
            "start_period": a.start_period,
            "duration": a.duration,
            "is_locked": a.is_locked,
            "course_name": course.name if course else "알 수 없음",
            "professor_id": prof.id if prof else 0,
            "professor_name": prof.name if prof else "알 수 없음",
            "department": course.department if course else "미지정",
            "grade": course.grade if course else 1,
            "section": course.section if course else "A",
            "room_name": room.name if room else "미지정",
            "building": room.building if room else "미지정",
            "is_computer_lab": room.is_computer_lab if room else False
        })

    return {
        "id": cand.id,
        "semester_id": cand.semester_id,
        "name": cand.name,
        "status": cand.status,
        "total_score": cand.total_score,
        "satisfaction_rate": cand.satisfaction_rate,
        "satisfied_soft_constraints": cand.satisfied_soft_constraints,
        "conflict_count": cand.conflict_count,
        "created_at": cand.created_at,
        "assignments": assignments_res
    }

@router.post("/generate", response_model=List[CandidateResponse])
def generate_timetables(
    req: GenerateTimetableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch DB data for semester
    professors = db.query(Professor).filter(Professor.semester_id == req.semester_id).all()
    rooms = db.query(Room).all()
    courses = db.query(Course).filter(Course.semester_id == req.semester_id).all()

    if not courses:
        raise HTTPException(status_code=400, detail="등록된 강의가 없어 시간표를 생성할 수 없습니다.")
    if not rooms:
        raise HTTPException(status_code=400, detail="등록된 강의실이 없어 시간표를 생성할 수 없습니다.")

    prof_data = [prof_to_response(p) for p in professors]
    room_data = [room_to_response(r) for r in rooms]
    course_data = [course_to_response(c, db) for c in courses]

    locked_assignments = []
    if req.locked_assignment_ids:
        locked_db = db.query(TimetableAssignment).filter(TimetableAssignment.id.in_(req.locked_assignment_ids)).all()
        for la in locked_db:
            locked_assignments.append({
                "course_id": la.course_id,
                "room_id": la.room_id,
                "day": la.day,
                "start_period": la.start_period
            })

    # Run OR-Tools CP-SAT solver
    try:
        solutions = solve_timetable(
            courses_data=course_data,
            rooms_data=room_data,
            professors_data=prof_data,
            locked_assignments=locked_assignments,
            num_solutions=req.num_candidates
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시간표 생성 중 오류가 발생했습니다: {str(e)}")

    if not solutions:
        raise HTTPException(status_code=400, detail="하드 제약조건을 만족하는 시간표 배합을 찾을 수 없습니다. 제약조건을 완화해주세요.")

    saved_candidates = []
    for sol in solutions:
        candidate = TimetableCandidate(
            semester_id=req.semester_id,
            name=sol["name"],
            status="CANDIDATE",
            total_score=sol["total_score"],
            satisfaction_rate=sol["satisfaction_rate"],
            satisfied_soft_constraints=sol["satisfied_soft_constraints"],
            conflict_count=sol["conflict_count"]
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        for assign_dict in sol["assignments"]:
            assignment = TimetableAssignment(
                candidate_id=candidate.id,
                course_id=assign_dict["course_id"],
                room_id=assign_dict["room_id"],
                day=assign_dict["day"],
                start_period=assign_dict["start_period"],
                duration=assign_dict["duration"],
                is_locked=assign_dict.get("is_locked", False)
            )
            db.add(assignment)
        db.commit()

        saved_candidates.append(candidate_to_response(candidate, db))

    # Audit log
    log_msg = f"시간표 추천안 {len(saved_candidates)}개 자동 생성 완료"
    if req.locked_assignment_ids:
        log_msg += f" (부분 재배정: {len(req.locked_assignment_ids)}개 강의 고정)"

    log = AuditLog(
        username=current_user.username,
        category="GENERATE",
        message=log_msg,
        details=json.dumps({"count": len(saved_candidates), "semester_id": req.semester_id})
    )
    db.add(log)
    db.commit()

    return saved_candidates

@router.get("/candidates", response_model=List[CandidateResponse])
def list_candidates(
    semester_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    candidates = db.query(TimetableCandidate).filter(TimetableCandidate.semester_id == semester_id).order_by(TimetableCandidate.id.desc()).all()
    return [candidate_to_response(c, db) for c in candidates]

@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cand = db.query(TimetableCandidate).filter(TimetableCandidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="추천안을 찾을 수 없습니다.")
    return candidate_to_response(cand, db)

@router.post("/validate-edit", response_model=ValidationResult)
def validate_edit(
    req: ManualEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(TimetableAssignment).filter(TimetableAssignment.id == req.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="배정 정보를 찾을 수 없습니다.")

    all_assignments = db.query(TimetableAssignment).filter(TimetableAssignment.candidate_id == req.candidate_id).all()
    courses = db.query(Course).all()
    rooms = db.query(Room).all()
    professors = db.query(Professor).all()

    prof_data = [prof_to_response(p) for p in professors]
    room_data = [room_to_response(r) for r in rooms]
    course_data = [course_to_response(c, db) for c in courses]
    assign_data = [{"course_id": a.course_id, "room_id": a.room_id, "day": a.day, "start_period": a.start_period, "duration": a.duration} for a in all_assignments]

    is_valid, conflicts = validate_manual_edit(
        target_course_id=assignment.course_id,
        new_day=req.new_day,
        new_start_period=req.new_start_period,
        new_room_id=req.new_room_id,
        all_assignments=assign_data,
        courses_data=course_data,
        rooms_data=room_data,
        professors_data=prof_data
    )

    return {"is_valid": is_valid, "conflicts": conflicts}

@router.post("/manual-edit", response_model=CandidateResponse)
def manual_edit_assignment(
    req: ManualEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(TimetableAssignment).filter(TimetableAssignment.id == req.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="배정 정보를 찾을 수 없습니다.")

    cand = db.query(TimetableCandidate).filter(TimetableCandidate.id == req.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="추천안을 찾을 수 없습니다.")

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    c_name = course.name if course else "강의"

    # Validate first
    all_assignments = db.query(TimetableAssignment).filter(TimetableAssignment.candidate_id == req.candidate_id).all()
    courses = db.query(Course).all()
    rooms = db.query(Room).all()
    professors = db.query(Professor).all()

    prof_data = [prof_to_response(p) for p in professors]
    room_data = [room_to_response(r) for r in rooms]
    course_data = [course_to_response(c, db) for c in courses]
    assign_data = [{"course_id": a.course_id, "room_id": a.room_id, "day": a.day, "start_period": a.start_period, "duration": a.duration} for a in all_assignments]

    is_valid, conflicts = validate_manual_edit(
        target_course_id=assignment.course_id,
        new_day=req.new_day,
        new_start_period=req.new_start_period,
        new_room_id=req.new_room_id,
        all_assignments=assign_data,
        courses_data=course_data,
        rooms_data=room_data,
        professors_data=prof_data
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=f"제약조건 위반으로 변경할 수 없습니다:\n" + "\n".join(conflicts))

    # Apply manual edit
    old_info = f"{assignment.day}요일 {assignment.start_period}교시"
    assignment.day = req.new_day
    assignment.start_period = req.new_start_period
    assignment.room_id = req.new_room_id
    assignment.is_locked = True # Mark as locked after manual modification
    db.commit()

    # Log edit history
    new_room = db.query(Room).filter(Room.id == req.new_room_id).first()
    r_name = new_room.name if new_room else "강의실"

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의 시간표 수동 변경 ({c_name}: {old_info} -> {req.new_day}요일 {req.new_start_period}교시 [{r_name}])",
        details=json.dumps({"assignment_id": req.assignment_id, "new_day": req.new_day, "new_period": req.new_start_period, "new_room": r_name})
    )
    db.add(log)
    db.commit()

    return candidate_to_response(cand, db)

@router.post("/toggle-lock/{assignment_id}", response_model=dict)
def toggle_lock(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    assignment = db.query(TimetableAssignment).filter(TimetableAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="배정 정보를 찾을 수 없습니다.")

    assignment.is_locked = not assignment.is_locked
    db.commit()

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    c_name = course.name if course else "강의"

    status_str = "고정(Lock)" if assignment.is_locked else "고정 해제"
    return {"message": f"{c_name} 수업이 {status_str}되었습니다.", "is_locked": assignment.is_locked}

@router.post("/confirm/{candidate_id}", response_model=CandidateResponse)
def confirm_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cand = db.query(TimetableCandidate).filter(TimetableCandidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="추천안을 찾을 수 없습니다.")

    # Reset other candidates to CANDIDATE and set this one to CONFIRMED
    db.query(TimetableCandidate).filter(TimetableCandidate.semester_id == cand.semester_id).update({"status": "CANDIDATE"})
    cand.status = "CONFIRMED"
    db.commit()

    log = AuditLog(
        username=current_user.username,
        category="CONFIRM",
        message=f"최종 학기 시간표 확정 ({cand.name})",
        details=json.dumps({"candidate_id": cand.id})
    )
    db.add(log)
    db.commit()

    return candidate_to_response(cand, db)
