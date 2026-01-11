from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionInfo(BaseModel):
    licenseplate: str
    started: datetime
    stopped: Optional[datetime]
    hours: float
    days: int


class ParkingInfo(BaseModel):
    name: str
    location: str
    tariff: float
    daytariff: float


class BillingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session: SessionInfo
    parking: ParkingInfo
    amount: Optional[float] = 0.0
    thash: str
    payed: float
    balance: Optional[float] = 0.0
