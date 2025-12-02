from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class Coordinates(BaseModel):
    lat: float
    lng: float

class UpdateCoordinates(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None

class ParkingLot(BaseModel):
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    address: str = Field(min_length=1)
    capacity: int = Field(ge=0)
    reserved: int = Field(ge=0)
    tariff: float = Field(ge=0)
    daytariff: float = Field(ge=0)
    created_at: str = Field(default=datetime.now().isoformat())
    coordinates: Coordinates

class UpdateParkingLot(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    capacity: Optional[int] = None
    reserved: Optional[int] = None
    tariff: Optional[float] = None
    daytariff: Optional[float] = None
    created_at: Optional[str] = None
    coordinates: Optional[Coordinates] = None

class ParkingSessionCreate(BaseModel):
    licenseplate: str

class UpdateParkingSessionOngoing(BaseModel):
    licenseplate: Optional[str] = None
    started: Optional[str] = None
    stopped: Optional[str] = None
    user: Optional[str] = None


class UpdateParkingSessionFinished(BaseModel):
    licenseplate: Optional[str] = None
    started: Optional[str] = None
    stopped: Optional[str] = None
    user: Optional[str] = None
    duration_minutes: Optional[int] = None
    cost: Optional[float] = None
    payment_status: Optional[str] = None