
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import Response as FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user
from app.models.log import Log
from app.response import error_response, success_response
from app.schemas.timetable import (
    AssignmentOut,
    CandidateOut,
    DraftRequest,
    GenerateRequest,
    ReassignRequest,
    TimetableOut,
    ValidateMoveRequest,
)
from app.services import timetable_service
from app.services.export_service import export_excel, export_pdf

router = APIRouter(prefix="/api/v1/timetables", tags=["시간표"])


# ── Generate ───────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_timetable(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """시간표 자동 생성 요청 — 202 Accepted + task_id 반환."""
    task_id = timetable_service.create_task()

    # Log generation event
    db.add(
        Log(
            log_type="GENERATE",
            user_id=current_user["user_id"],
            username=current_user["username"],
            detail={"task_id": task_id, "semester_id": body.semester_id},
        )
    )
    db.commit()

    # Pass the coroutine *function* (not the coroutine) so FastAPI BackgroundTasks
    # can properly await it. Using asyncio.ensure_future was wrong here.
    background_tasks.add_task(
        timetable_service.run_generation_async,
        db_factory=SessionLocal,
        task_id=task_id,
        semester_id=body.semester_id,
        min_candidates=body.min_candidates,
    )

    return success_response(data={"task_id": task_id}, status_code=202)


@router.get("/tasks/{task_id}")
def get_task_status(
    task_id: str,
    _: dict = Depends(get_current_user),
):
    """비동기 생성 작업 상태 조회."""
    task = timetable_service.get_task(task_id)
    status = task["status"]
    message = None

    if status == timetable_service.TASK_INFEASIBLE:
        message = "제약조건을 모두 만족하는 시간표 생성 불가"
    elif status == timetable_service.TASK_FAILED:
        message = task.get("error", "알 수 없는 오류가 발생했습니다.")

    return success_response(
        data={
            "task_id": task_id,
            "status": status,
            "message": message,
            "candidate_ids": task.get("candidates", []),
        }
    )


# ── Candidates ─────────────────────────────────────────────────────────────────

@router.get("/candidates")
def list_candidates(
    semester_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """추천안 목록 조회."""
    candidates = timetable_service.list_candidates(db, semester_id)
    return success_response(data=[CandidateOut.model_validate(c).model_dump() for c in candidates])


# ── Views ──────────────────────────────────────────────────────────────────────

@router.get("/views")
def get_timetable_view(
    semester_id: int,
    type: str = "room",
    target_name: str | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """조건별 시간표 조회 (강의실/교수/학년/학과)."""
    data = timetable_service.get_timetable_view(db, semester_id, type, target_name)
    return success_response(data=data)


# ── Validate move ──────────────────────────────────────────────────────────────

@router.post("/validate-move")
def validate_move(
    body: ValidateMoveRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """수동 변경 충돌 실시간 검증."""
    result = timetable_service.validate_move(
        db,
        body.timetable_id,
        body.assignment_id,
        body.target_room_id,
        body.target_day,
        body.target_start_period,
    )
    return success_response(data=result)


# ── Partial reassign ───────────────────────────────────────────────────────────

@router.post("/reassign")
async def partial_reassign(
    body: ReassignRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """일부 강의를 고정한 채 나머지만 재배정."""
    tt = timetable_service.get_timetable(db, body.timetable_id)
    task_id = timetable_service.create_task()

    # Mark fixed assignments before async run
    # (The engine will receive fixed_assignment_ids in a future enhancement)
    db.add(
        Log(
            log_type="GENERATE",
            user_id=current_user["user_id"],
            username=current_user["username"],
            detail={"action": "reassign", "timetable_id": body.timetable_id, "task_id": task_id},
        )
    )
    db.commit()

    background_tasks.add_task(
        asyncio.ensure_future,
        timetable_service.run_generation_async(
            db_factory=SessionLocal,
            task_id=task_id,
            semester_id=tt.semester_id,
            min_candidates=1,
        ),
    )
    return success_response(data={"task_id": task_id}, status_code=202)


# ── Draft & Confirm ────────────────────────────────────────────────────────────

@router.post("/{timetable_id}/draft")
def save_draft(
    timetable_id: int,
    body: DraftRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """시간표 임시 저장 (Optimistic Locking)."""
    tt = timetable_service.save_draft(
        db,
        timetable_id,
        body.version,
        [a.model_dump() for a in body.assignments],
    )
    db.add(
        Log(
            log_type="MODIFY",
            user_id=current_user["user_id"],
            username=current_user["username"],
            detail={"action": "draft", "timetable_id": timetable_id},
        )
    )
    db.commit()
    return success_response(data={"timetable_id": tt.id, "version": tt.version, "status": tt.status})


@router.post("/{timetable_id}/confirm")
def confirm_timetable(
    timetable_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """시간표 최종 확정."""
    tt = timetable_service.confirm_timetable(db, timetable_id)
    db.add(
        Log(
            log_type="MODIFY",
            user_id=current_user["user_id"],
            username=current_user["username"],
            detail={"action": "confirm", "timetable_id": timetable_id},
        )
    )
    db.commit()
    return success_response(data={"timetable_id": tt.id, "status": tt.status}, message="시간표가 최종 확정되었습니다.")


# ── Export ─────────────────────────────────────────────────────────────────────

@router.get("/{timetable_id}/export")
def export_timetable(
    timetable_id: int,
    format: str = "excel",
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """시간표 파일 내보내기 (pdf | excel)."""
    if format == "pdf":
        content = export_pdf(db, timetable_id)
        media_type = "application/pdf"
        filename = f"timetable_{timetable_id}.pdf"
    else:
        content = export_excel(db, timetable_id)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"timetable_{timetable_id}.xlsx"

    return FileResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Detail ─────────────────────────────────────────────────────────────────────

@router.get("/{timetable_id}")
def get_timetable(
    timetable_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """시간표 상세 조회 (배정 목록 포함)."""
    tt = timetable_service.get_timetable(db, timetable_id)
    assignments = timetable_service.get_assignments(db, timetable_id)
    data = TimetableOut.model_validate(tt).model_dump()
    data["assignments"] = [AssignmentOut.model_validate(a).model_dump() for a in assignments]
    return success_response(data=data)
