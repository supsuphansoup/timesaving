from datetime import datetime

from pydantic import BaseModel, Field


# ── Generate ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    min_candidates: int = Field(default=3, ge=1, le=10)


class GenerateResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    # PROCESSING | COMPLETED | INFEASIBLE | FAILED
    status: str
    message: str | None = None


# ── Candidate ─────────────────────────────────────────────────────────────────

class CandidateOut(BaseModel):
    id: int
    task_id: str | None
    rank: int
    score: float
    pref_rate: float
    fitness_rate: float
    conflict_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Assignment ────────────────────────────────────────────────────────────────

class AssignmentOut(BaseModel):
    id: int
    timetable_id: int
    course_id: int
    # 온라인 수업(0교시)은 강의실이 없어 None이다.
    room_id: int | None = None
    day: str
    start_period: int
    duration: int
    
    # Enriched fields (populated dynamically)
    course_name: str | None = None
    professor_id: int | None = None
    professor_name: str | None = None
    department: str | None = None
    grade: int | None = None
    section: str | None = None
    room_name: str | None = None
    building: str | None = None
    is_computer_lab: bool = False
    is_locked: bool = False

    model_config = {"from_attributes": True}


class AssignmentIn(BaseModel):
    course_id: int
    room_id: int | None = None
    day: str
    start_period: int = Field(..., ge=0, le=9)
    duration: int = Field(default=1, ge=1)


# ── Validate move ─────────────────────────────────────────────────────────────

class ValidateMoveRequest(BaseModel):
    timetable_id: int
    assignment_id: int
    target_room_id: int
    target_day: str
    target_start_period: int = Field(..., ge=0, le=9)


# ── Partial reassign ──────────────────────────────────────────────────────────

class ReassignRequest(BaseModel):
    timetable_id: int
    fixed_assignment_ids: list[int] = Field(default_factory=list)


# ── Draft ─────────────────────────────────────────────────────────────────────

class DraftRequest(BaseModel):
    version: int
    assignments: list[AssignmentIn]


# ── Timetable detail ──────────────────────────────────────────────────────────

class TimetableOut(BaseModel):
    id: int
    name: str | None
    status: str
    version: int
    score: float
    pref_rate: float
    fitness_rate: float
    conflict_count: int
    task_id: str | None
    rank: int
    created_at: datetime
    updated_at: datetime
    assignments: list[AssignmentOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class SwapRequest(BaseModel):
    timetable_id: int
    assignment1_id: int
    assignment2_id: int
