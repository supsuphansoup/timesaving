from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Timetable(Base):
    """A timetable candidate or confirmed timetable for a semester."""

    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=True)

    # Status: CANDIDATE | DRAFT | CONFIRMED
    status: Mapped[str] = mapped_column(String(20), default="CANDIDATE")

    # Optimistic locking version counter
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Scoring metrics
    score: Mapped[float] = mapped_column(Float, default=0.0)
    pref_rate: Mapped[float] = mapped_column(Float, default=0.0)
    fitness_rate: Mapped[float] = mapped_column(Float, default=0.0)
    conflict_count: Mapped[int] = mapped_column(Integer, default=0)

    # Which generation task produced this timetable
    task_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # Rank among candidates from same task (1 = best)
    rank: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Assignment(Base):
    """A single course-to-room-time assignment within a timetable."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timetable_id: Mapped[int] = mapped_column(Integer, ForeignKey("timetables.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    # 온라인 수업(0교시)은 강의실을 쓰지 않으므로 NULL이다.
    room_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("rooms.id"), nullable=True
    )

    # Day: MON | TUE | WED | THU | FRI
    day: Mapped[str] = mapped_column(String(3), nullable=False)

    # Starting period (0–9)
    start_period: Mapped[int] = mapped_column(Integer, nullable=False)

    # How many consecutive periods this assignment occupies
    duration: Mapped[int] = mapped_column(Integer, default=1)
    is_locked: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
