from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime


class VehicleCreate(BaseModel):
    user_id: str
    license_plate: str = Field(..., min_length=6, max_length=8)
    make: str
    model: str
    color: str
    year: int

    @field_validator("license_plate")
    @classmethod
    def validate_dutch_license_plate(cls, v: str) -> str:
        if not v:
            raise ValueError("License plate cannot be empty")
        plate = v.upper()
        dutch_patterns = [
            r"^[A-Z]{2}-\d{2}-\d{2}$",  # XX-99-99
            r"^\d{2}-[A-Z]{2}-\d{2}$",  # 99-XX-99
            r"^\d{2}-\d{2}-[A-Z]{2}$",  # 99-99-XX
            r"^[A-Z]{2}-\d{2}-[A-Z]{2}$",  # XX-99-XX
            r"^\d{2}-[A-Z]{2}-[A-Z]{2}$",  # 99-XX-XX
            r"^[A-Z]{2}-[A-Z]{2}-\d{2}$",  # XX-XX-99
            r"^[A-Z]{1}-\d{3}-[A-Z]{2}$",  # X-999-XX
            r"^[A-Z]{2}-\d{3}-[A-Z]{1}$",  # XX-999-X
            r"^\d{3}-[A-Z]{2}-[A-Z]{1}$",  # 999-XX-X
            r"^[A-Z]{1}-\d{4}-[A-Z]{1}$",  # X-9999-X
        ]
        if not any(re.match(pattern, plate) for pattern in dutch_patterns):
            raise ValueError("Invalid dutch license plate format")
        return plate


class VehicleOut(BaseModel):
    id: str
    user_id: str
    license_plate: str
    make: str
    model: str
    color: str
    year: int
    created_at: datetime
    # updated_at: datetime
