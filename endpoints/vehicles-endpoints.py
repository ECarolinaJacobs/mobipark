from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from models.vehicles import VehicleCreate, VehicleOut
from storage_utils import load_json, save_data
from session_manager import get_session

router = APIRouter(tags=["vehicles"])

DATA_PATH = "data/vehicles.json"


@router.post("/vehicles", response_model=VehicleOut)
def create_vehicle(payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})

    lid = payload.license_plate.replace("-", "")
    if lid in uvehicles:
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    new_vehicle = VehicleOut(
        license_plate=payload.license_plate,
        name=payload.name,
    )
    if not uvehicles:
        vehicles[session_user["username"]] = {}
    vehicles[session_user["username"]][lid] = new_vehicle.model_dump()  # new method instead of dict()
    save_data(DATA_PATH, vehicles)
    return new_vehicle


@router.get("/vehicles", response_model=dict)
def get_user_vehicles(authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    return vehicles.get(session_user["username"], {})


@router.put("/vehicles/{license_plate}", response_model=VehicleOut)
def update_vehicle(license_plate: str, payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})
    lid = license_plate.replace("-", "")
    if lid not in uvehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    uvehicles[lid]["name"] = payload.name
    save_data(DATA_PATH, vehicles)
    return VehicleOut(**uvehicles[lid])


@router.delete("/vehicles/{license_plate}")
def delete_vehicle(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})

    lid = license_plate.replace("-", "")
    if lid not in uvehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    del vehicles[session_user["username"]][lid]
    save_data(DATA_PATH, vehicles)
    return {"status": "Deleted"}


@router.get("/vehicles/{license_plate}/reservations")
def get_vehicle_reservations(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})

    lid = license_plate.replace("-", "")
    if lid not in uvehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"reservations": []}  # probably a placeholder for future reservations integration


@router.get("/vehicles/{license_plate}/history")
def get_vehicle_history(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})

    lid = license_plate.replace("-", "")
    if lid not in uvehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"history": []}  # probably a placeholder until sessions or billig module integration
