from pydantic import BaseModel, Field
from typing import Optional


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = Field(None, min_length=8)
    birth_year: Optional[int] = Field(None, ge=1900, le=2100)


class ProfileResponse(BaseModel):
    id: str
    username: str
    name: str | None
    email: str | None
    phone: str | None
    role: str
    created_at: str
    birth_year: int | None
    active: bool
