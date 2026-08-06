from datetime import datetime

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    room_name: str = Field(..., min_length=1)
    location: str | None = None
    capacity: int = Field(..., ge=1)
    is_computer_room: bool = False
    is_common_room: bool = False
    remarks: str | None = None


class RoomUpdate(BaseModel):
    room_name: str | None = None
    location: str | None = None
    capacity: int | None = None
    is_computer_room: bool | None = None
    is_common_room: bool | None = None
    remarks: str | None = None


class RoomOut(BaseModel):
    id: int
    room_name: str
    location: str | None
    capacity: int
    is_computer_room: bool
    is_common_room: bool
    remarks: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
