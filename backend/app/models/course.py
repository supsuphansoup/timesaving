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
    class_section: Mapped[str] = mapped_column(String(8), nullable=False)    # "A", "B", …
    weekly_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    expected_students: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_computer: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Scheduling constraints (hard) ────────────────────────────────────────
    # Days the course ideally should not be scheduled e.g. ["MON", "FRI"]
    non_preferred_days: Mapped[list] = mapped_column(JSON, default=list)
    # Period indices the course ideally should not use e.g. [1, 2]
    non_preferred_periods: Mapped[list] = mapped_column(JSON, default=list)
    # Room IDs that must be used (empty = any)
    fixed_room_ids: Mapped[list] = mapped_column(JSON, default=list)
    # Room IDs that cannot be used
    unavailable_room_ids: Mapped[list] = mapped_column(JSON, default=list)

    # ── Scheduling constraints (soft / preferences) ───────────────────────────
    preferred_days: Mapped[list] = mapped_column(JSON, default=list)
    preferred_periods: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
