from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Timetable(Base):
    """A timetable candidate or confirmed timetable for a semester."""

    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    semester_id: Mapped[int] = mapped_column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=True)

    # Status: CANDIDATE | DRAFT | CONFIRMED
    status: Mapped[str] = mapped_column(String(20), default="CANDIDATE")

    # Optimistic locking version counter
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Scoring metrics
    score: Mapped[float] = mapped_column(Float, default=0.0)
    constraint_satisfaction_rate: Mapped[float] = mapped_column(Float, default=0.0)
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
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)

    # Day: MON | TUE | WED | THU | FRI
    day: Mapped[str] = mapped_column(String(3), nullable=False)

    # Starting period (1–9)
    start_period: Mapped[int] = mapped_column(Integer, nullable=False)

    # How many consecutive periods this assignment occupies
    duration: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
