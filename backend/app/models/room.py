from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Room(Base):
    """Classroom / lecture room with availability and capacity info."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    location: Mapped[str] = mapped_column(String(128), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_computer_room: Mapped[bool] = mapped_column(Boolean, default=False)

    # Time strings like "09:00-18:00" or comma-separated ranges
    available_time: Mapped[str] = mapped_column(String(64), nullable=True)
    unavailable_time: Mapped[str] = mapped_column(String(64), nullable=True)

    is_common_room: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
