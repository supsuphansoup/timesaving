from datetime import datetime

from pydantic import BaseModel, Field


class ProfessorCreate(BaseModel):
    name: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)


class ProfessorUpdate(BaseModel):
    name: str | None = None
    department: str | None = None


class ProfessorOut(BaseModel):
    id: int
    name: str
    department: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
