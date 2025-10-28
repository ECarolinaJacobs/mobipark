from pydantic import BaseModel
from datetime import date, datetime

class Coordinates(BaseModel):
    lat: float
    lng: float

class ParkingLot(BaseModel):
    name: str
    location: str
    address: str
    capacity: int
    reserved: int
    tariff: float
    daytariff: float
    created_at: date
    coordinates: Coordinates

class ParkingSessionCreate(BaseModel):
    licenseplate: str

class OngoingParkingSession(BaseModel):
    licenseplate: str
    started: str
    stopped: str
    user: str

class FinishedParkingSession(BaseModel):
    licenseplate: str
    started: str
    stopped: str
    user: str
    duration_minutes: int
    cost: float
    payment_status: str