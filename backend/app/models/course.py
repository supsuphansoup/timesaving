from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class Course(Base):
    """A course/lecture linked to a professor and semester.

    Scheduling constraints (availability, preferences, room requirements)
    are stored here per-course, rather than on the professor, so that
    the same professor can have different constraints for different courses.
    """

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_name: Mapped[str] = mapped_column(String(128), nullable=False)
    professor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("professors.id"), nullable=False, index=True
    )
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    target_grade: Mapped[int] = mapped_column(Integer, nullable=False)       # 1–4
    # 분반 — 학부 시간표 표기 관례를 따라 "101", "102", … 형식을 사용한다.
    # (엑셀 출력이 `과목명_분반_교수명` 형태이므로 표기가 그대로 노출된다)
    class_section: Mapped[str] = mapped_column(String(8), nullable=False)
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # 온라인(비대면) 수업 시수. 0이면 전부 대면.
    # 온라인 수업은 0교시에만 열리며 강의실을 점유하지 않는다.
    online_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_students: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_computer: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Scheduling constraints (hard) ────────────────────────────────────────
    # NOTE: despite the "non_preferred" name these are HARD constraints
    # (요구사항 명세서 HC-03 / HC-04, "불가 요일" / "불가 교시").
    # The engine never creates decision variables for these slots — they are
    # excluded outright, not merely penalized.
    #
    # 불가 요일 (HC-03) — the course is never scheduled on these days e.g. ["MON", "FRI"]
    non_preferred_days: Mapped[list] = mapped_column(JSON, default=list)
    # 불가 교시 (HC-04) — the course never uses these period indices e.g. [1, 2]
    non_preferred_periods: Mapped[list] = mapped_column(JSON, default=list)
    # Room IDs that must be used (empty = any)
    fixed_room_ids: Mapped[list] = mapped_column(JSON, default=list)
    # Room IDs that cannot be used
    unavailable_room_ids: Mapped[list] = mapped_column(JSON, default=list)

    # Block mapping preference e.g. "3", "2+1", "1+1+1"
    block_preference: Mapped[str] = mapped_column(String(32), nullable=True)
    # List of course names or substrings that this course must NOT overlap with
    mutually_exclusive_with: Mapped[list] = mapped_column(JSON, default=list)
    # Exact forced schedules e.g. [{"day": "MON", "period": 0}]
    fixed_schedules: Mapped[list] = mapped_column(JSON, default=list)
    # Target cohorts for overlap prevention e.g. ["소프트웨어_1", "컴공_1"]
    target_cohorts: Mapped[list] = mapped_column(JSON, default=list)

    # ── Scheduling constraints (soft / preferences) ───────────────────────────
    preferred_days: Mapped[list] = mapped_column(JSON, default=list)
    preferred_periods: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
