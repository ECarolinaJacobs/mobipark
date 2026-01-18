from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re
import uuid

ISO_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"


class CreateReservation(BaseModel):
    user_id: Optional[str] = Field(None, description = "Optional user id", json_schema_extra = {"example": "test"})
    vehicle_id: str = Field(...,description= "Vehicle identifier (UUID)", json_schema_extra= {"example": "5312672-bba0-497d-97d7-032c3c28b51c"})
    start_time: str = Field(..., description="Start time of the reservation in ISO format", json_schema_extra={"example":"2025-12-06T10:00"})
    end_time: str = Field(..., description="End time of the reservation in ISO format", json_schema_extra={"example":"2025-12-06T10:00"})
    parking_lot_id: str = Field(..., description = "Parking lot numeric identifier", json_schema_extra = {"example": "1"})
    status: str = Field(default="pending", description= "Reservation status", json_schema_extra= {"example":"pending"})
    created_at: Optional[str] = Field(default=None, description="Creation time of reservation in ISO format",json_schema_extra={"example": "2026-12-01T10:34"})

    @field_validator("vehicle_id")
    def validate_vehicle_id(cls, value):
        try:
            uuid.UUID(str(value))
        except ValueError:
            raise ValueError("Vehicle id must be a valid uuid")
        return str(value)

    @field_validator("start_time", "end_time")
    def validate_iso_datetime(cls, value):
        if not re.match(ISO_REGEX, value):
            raise ValueError("Date must be in iso format: YYYY-MM-DDTHH:MM")
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValueError("Invalid iso datetime")
        return value

    @field_validator("parking_lot_id")
    def validate_parking_lot_id(cls, value):
        if not value.isdigit():
            raise ValueError("Parking lot id must be a digit")
        return value


class UpdateReservation(BaseModel):
    user_id: Optional[str] = Field(default=None, description = "Optional user id", json_schema_extra = {"example": "test"})
    vehicle_id: str = Field(...,description= "Vehicle identifier (UUID)", json_schema_extra= {"example": "5312672-bba0-497d-97d7-032c3c28b51c"})
    start_time: str = Field(..., description="Start time of the reservation in ISO format", json_schema_extra={"example":"2025-12-06T10:00"})
    end_time: str = Field(..., description="End time of the reservation in ISO format", json_schema_extra={"example":"2025-12-06T10:00"})
    parking_lot_id: str = Field(..., description = "Parking lot numeric identifier", json_schema_extra = {"example": "1"})
    status: Optional[str] = Field(None, description= "Reservation status", json_schema_extra= {"example":"pending"})
    cost: Optional[float] = Field(None, description="Total cost of the reservation", json_schema_extra={"example":10.50})

    @field_validator("vehicle_id")
    def validate_vehicle_id(cls, value):
        try:
            uuid.UUID(str(value))
        except ValueError:
            raise ValueError("Vehicle id must be a valid uuid")
        return str(value)

    @field_validator("start_time", "end_time")
    def validate_iso_datetime(cls, value):
        if not re.match(ISO_REGEX, value):
            raise ValueError("Date must be in iso format: YYYY-MM-DDTHH:MM")
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValueError("Invalid iso datetime")
        return value

    @field_validator("parking_lot_id")
    def validate_parking_lot_id(cls, value):
        if not value.isdigit():
            raise ValueError("Parking lot ID must be a digit")
        return value


class Reservation(CreateReservation):
    id: str = Field(...,description="Reservation id", json_schema_extra={"example": "10"})

    @field_validator("id")
    def validate_id(cls, value):
        if not value.isdigit():
            raise ValueError("ID must be a digit")
        return value
