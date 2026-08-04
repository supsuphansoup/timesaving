from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Professor(Base):
    """Professor — identifies who teaches; constraints are now on the Course level."""

    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    semester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("semesters.id"), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
