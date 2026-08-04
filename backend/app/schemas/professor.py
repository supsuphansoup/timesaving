from datetime import datetime

from pydantic import BaseModel, Field


class ProfessorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    semester_id: int


class ProfessorUpdate(BaseModel):
    name: str | None = None
    department: str | None = None


class ProfessorOut(BaseModel):
    id: int
    name: str
    department: str
    semester_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
