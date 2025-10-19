from pydantic import BaseModel


class VehicleCreate(BaseModel):
    name: str
    license_plate: str


class VehicleOut(BaseModel):
    license_plate: str
    name: str
