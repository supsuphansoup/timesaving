from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class Log(Base):
    """Audit log for login / generate / modify events."""

    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # LOGIN | GENERATE | MODIFY
    log_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # nullable because system events may not have a user
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True)

    # Arbitrary JSON detail payload (diff, params, etc.)
    detail: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
