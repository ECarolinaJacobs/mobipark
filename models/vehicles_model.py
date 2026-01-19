from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime
from typing import List


class VehicleCreate(BaseModel):
    """Model for creating a new vehicle"""

    license_plate: str = Field(
        ..., min_length=6, max_length=8, description="Dutch license plate", examples=["AB-123-CD"]
    )
    make: str = Field(..., description="Vehicle manufacturer", examples=["Toyota"])
    model: str = Field(..., description="Vehicle model", examples=["Corolla"])
    color: str = Field(..., description="Vehicle color", examples=["Red"])
    year: int = Field(..., description="Manufacturing year", examples=[2020])

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
    id: str = Field(..., description="Unique vehicle ID")
    user_id: str = Field(..., description="Owner's username")
    license_plate: str = Field(..., description="Vehicle license plate")
    make: str = Field(..., description="Vehicle manufacturer")
    model: str = Field(..., description="Vehicle model")
    color: str = Field(..., description="Vehicle color")
    year: int = Field(..., description="Manufacturing year")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")


class VehicleListResponse(BaseModel):
    """list of vehicles"""

    vehicles: List[VehicleOut]


class DeleteResponse(BaseModel):
    """Deletion confirmation"""

    status: str = Field(..., examples=["Deleted"])


class VehicleReservationsResponse(BaseModel):
    """Vehicle reservations list"""

    reservations: List[dict]


class VehicleHistoryResponse(BaseModel):
    """Vehicle parking history"""

    history: List[dict]
