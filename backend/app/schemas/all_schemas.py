from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    name: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str

    class Config:
        from_attributes = True

# --- Professor Schemas ---
class ProfessorBase(BaseModel):
    name: str
    department: str
    phone: Optional[str] = None
    email: Optional[str] = None
    unavailable_days: List[str] = []       # e.g. ["월", "금"]
    preferred_days: List[str] = []         # e.g. ["화", "목"]
    unavailable_periods: List[int] = []    # e.g. [1, 2, 8, 9]
    preferred_periods: List[int] = []      # e.g. [3, 4, 5, 6]
    unavailable_slots: List[str] = []      # e.g. ["월-1", "화-3"]
    preferred_slots: List[str] = []        # e.g. ["수-5", "목-6"]
    fixed_room_id: Optional[int] = None
    unavailable_room_ids: List[int] = []   # e.g. [2]
    weekly_hours_limit: int = 15

class ProfessorCreate(ProfessorBase):
    semester_id: int = 1

class ProfessorUpdate(ProfessorBase):
    pass

class ProfessorResponse(ProfessorBase):
    id: int
    semester_id: int

    class Config:
        from_attributes = True

# --- Room Schemas ---
class RoomBase(BaseModel):
    name: str
    building: str
    capacity: int
    is_computer_lab: bool = False
    is_common: bool = False
    available_hours: List[Any] = []
    unavailable_hours: List[Dict[str, Any]] = [] # e.g. [{"day": "수", "periods": [1, 2]}]
    notes: Optional[str] = None

class RoomCreate(RoomBase):
    pass

class RoomUpdate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int

    class Config:
        from_attributes = True

# --- Course Schemas ---
class CourseBase(BaseModel):
    name: str
    professor_id: int
    department: str
    grade: int = 1
    section: str = "A"
    weekly_hours: int = 3
    expected_students: int = 30
    computer_required: bool = False
    fixed_room_id: Optional[int] = None

class CourseCreate(CourseBase):
    semester_id: int = 1

class CourseUpdate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    semester_id: int
    professor_name: Optional[str] = None
    fixed_room_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Timetable Schemas ---
class AssignmentBase(BaseModel):
    course_id: int
    room_id: int
    day: str
    start_period: int
    duration: int
    is_locked: bool = False

class AssignmentResponse(AssignmentBase):
    id: int
    course_name: str
    professor_id: int
    professor_name: str
    department: str
    grade: int
    section: str
    room_name: str
    building: str
    is_computer_lab: bool

    class Config:
        from_attributes = True

class CandidateResponse(BaseModel):
    id: int
    semester_id: int
    name: str
    status: str
    total_score: float
    satisfaction_rate: float
    satisfied_soft_constraints: int
    conflict_count: int
    created_at: datetime
    assignments: List[AssignmentResponse] = []

    class Config:
        from_attributes = True

class GenerateTimetableRequest(BaseModel):
    semester_id: int = 1
    num_candidates: int = 3
    locked_assignment_ids: List[int] = [] # 부분 재배정용 고정 강의 목록

class ManualEditRequest(BaseModel):
    candidate_id: int
    assignment_id: int
    new_day: str
    new_start_period: int
    new_room_id: int

class ValidationResult(BaseModel):
    is_valid: bool
    conflicts: List[str] = []

# --- Audit Log Schemas ---
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    username: str
    category: str
    message: str
    details: Optional[str] = None

    class Config:
        from_attributes = True
