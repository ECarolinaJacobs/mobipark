from pydantic import BaseModel
from typing import Optional

class CreateReservation(BaseModel):
    user : Optional[str]  = None # Extra field if session user is admin
    vehicle_id: str
    start_time: str
    end_time: str
    parking_lot_id: str

class UpdateReservation(BaseModel):
    user : Optional[str]  # Extra field if session user is admin
    vehicle_id: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    parking_lot_id: Optional[str]












