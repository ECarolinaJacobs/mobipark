from pydantic import BaseModel, Field, field_validator
from typing import Optional
import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    name: str
    password: str
    role: Optional[str] = "USER"
    managed_parking_lot_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_year: Optional[int] = None

class User(BaseModel):
    id: str = Field(default="")
    username: Optional[str] = None
    password: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "USER"
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d")
    )
    birth_year: Optional[int] = None
    active: bool = True
    managed_parking_lot_id: Optional[str] = None
