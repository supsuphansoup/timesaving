from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    course_name: str = Field(..., min_length=1)
    professor_id: int
    department: str = Field(..., min_length=1)
    target_grade: int = Field(..., ge=1, le=4)
    class_section: str = Field(..., min_length=1)
    weekly_hours: int = Field(default=3, ge=1, le=9)
    expected_students: int = Field(..., ge=1)
    requires_computer: bool = False

    # ── Scheduling constraints (hard) ────────────────────────────────────────
    # Allowed values for days: "MON" | "TUE" | "WED" | "THU" | "FRI"
    non_preferred_days: list[str] = Field(default_factory=list)
    non_preferred_periods: list[int] = Field(default_factory=list)  # 1-based period indices
    fixed_room_ids: list[int] = Field(default_factory=list)
    unavailable_room_ids: list[int] = Field(default_factory=list)

    # ── Scheduling constraints (soft / preferences) ───────────────────────────
    preferred_days: list[str] = Field(default_factory=list)
    preferred_periods: list[int] = Field(default_factory=list)


class CourseUpdate(BaseModel):
    course_name: str | None = None
    professor_id: int | None = None
    department: str | None = None
    target_grade: int | None = None
    class_section: str | None = None
    weekly_hours: int | None = None
    expected_students: int | None = None
    requires_computer: bool | None = None

    # Constraints can also be updated individually
    non_preferred_days: list[str] | None = None
    non_preferred_periods: list[int] | None = None
    fixed_room_ids: list[int] | None = None
    unavailable_room_ids: list[int] | None = None
    preferred_days: list[str] | None = None
    preferred_periods: list[int] | None = None


class CourseOut(BaseModel):
    id: int
    course_name: str
    professor_id: int
    department: str
    target_grade: int
    class_section: str
    weekly_hours: int
    expected_students: int
    requires_computer: bool

    non_preferred_days: list[str]
    non_preferred_periods: list[int]
    fixed_room_ids: list[int]
    unavailable_room_ids: list[int]
    preferred_days: list[str]
    preferred_periods: list[int]

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
