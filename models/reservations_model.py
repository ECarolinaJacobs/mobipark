from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re
import uuid

ISO_REGEX = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$"

class CreateReservation(BaseModel):
    user_id: Optional[str] = None 
    vehicle_id: str
    start_time: str
    end_time: str
    parking_lot_id: str
    status: str = "pending"
    created_at: Optional[str] = None

    @field_validator('vehicle_id') 
    def validate_vehicle_id(cls, value): 
        try: 
            uuid.UUID(str(value)) 
        except ValueError: 
            raise ValueError("Vehicle id must be a valid uuid") 
        return str(value)

    @field_validator('start_time', 'end_time')
    def validate_iso_datetime(cls, value):
        if not re.match(ISO_REGEX, value):
            raise ValueError("Date must be in iso format: YYYY-MM-DDTHH:MMZ")
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%MZ")
        except ValueError:
            raise ValueError("Invalid iso datetime")
        return value

    @field_validator('parking_lot_id')
    def validate_parking_lot_id(cls, value):
        if not value.isdigit():
            raise ValueError("Parking lot id must be a digit")
        return value



class UpdateReservation(BaseModel):
    user_id: Optional[str] = None
    vehicle_id: str
    start_time: str
    end_time: str
    parking_lot_id: str
    status : Optional[str] = None
    cost: Optional[float] = None

    @field_validator('vehicle_id') 
    def validate_vehicle_id(cls, value): 
        try: 
            uuid.UUID(str(value)) 
        except ValueError: 
            raise ValueError("Vehicle id must be a valid uuid") 
        return str(value)

    @field_validator('start_time', 'end_time')
    def validate_iso_datetime(cls, value):
        if not re.match(ISO_REGEX, value):
            raise ValueError("Date must be in iso format: YYYY-MM-DDTHH:MMZ")
        try:
            datetime.strptime(value, "%Y-%m-%dT%H:%MZ")
        except ValueError:
            raise ValueError("Invalid iso datetime")
        return value

    @field_validator('parking_lot_id')
    def validate_parking_lot_id(cls, value):
        if not value.isdigit():
            raise ValueError("Parking lot ID must be a digit")
        return value

class Reservation(CreateReservation):
    id: str
    
    @field_validator('id')
    def validate_id(cls, value):
        if not value.isdigit():
            raise ValueError("ID must be a digit")
        return value