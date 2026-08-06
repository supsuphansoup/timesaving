from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=4)
    password: str = Field(..., min_length=4)
    password_confirm: str = Field(..., min_length=4)
    name: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
