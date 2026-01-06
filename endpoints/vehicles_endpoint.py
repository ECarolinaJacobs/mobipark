from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime
import uuid

from models.vehicles_model import VehicleCreate, VehicleOut
from utils.storage_utils import (
    get_vehicle_data_by_user,
    update_existing_vehicle_in_db,
    delete_vehicle_from_db,
    load_vehicle_data_from_db,
    save_new_vehicle_to_db,
    load_reservation_data_from_db,
)
from utils.session_manager import get_session


router = APIRouter(tags=["vehicles"])


def normalize_plate(p: str) -> str:
    if not p:
        return ""
    return p.replace("-", "").upper().strip()


def find_vehicle_by_license_plate(license_plate: str):
    lid = normalize_plate(license_plate)
    vehicles = load_vehicle_data_from_db()
    for v in vehicles:
        if normalize_plate(v.get("license_plate", "")) == lid:
            return v
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.post(
    "/vehicles",
    summary="Create a new Vehicle",
    response_description="Created vehicle details",
    response_model=VehicleOut,
)
def create_vehicle(payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    vehicles = load_vehicle_data_from_db()

    for v in vehicles:
        if normalize_plate(v["license_plate"]) == normalize_plate(payload.license_plate):
            raise HTTPException(status_code=400, detail="Vehicle already exists")
    new_vehicle = {
        "id": str(uuid.uuid4()),
        "user_id": str(session_user["username"]),
        "license_plate": payload.license_plate,
        "make": payload.make,
        "model": payload.model,
        "color": payload.color,
        "year": payload.year,
        "created_at": datetime.now().isoformat(),
    }
    try:
        save_new_vehicle_to_db(new_vehicle)
    except Exception:
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    return new_vehicle


@router.get("/vehicles/{username}", response_model=dict)
@router.get("/vehicles", response_model=dict)
def get_user_vehicles(username: Optional[str] = None, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    if not username:
        username = session_user["username"]
    is_admin = session_user.get("role", "").upper() == "ADMIN"
    if username != session_user["username"] and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    vehicles = get_vehicle_data_by_user(username)
    return {"vehicles": vehicles}


@router.put("/vehicles/{license_plate}", response_model=VehicleOut)
def update_vehicle(license_plate: str, payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    # find the owner for this vehicle
    target_vehicle = find_vehicle_by_license_plate(license_plate)
    if target_vehicle["user_id"] != session_user["username"] and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: cannot modify another users vehicle")
    target_vehicle.update(
        {
            "license_plate": payload.license_plate,
            "make": payload.make,
            "model": payload.model,
            "color": payload.color,
            "year": payload.year,
        }
    )
    update_existing_vehicle_in_db(target_vehicle["id"], target_vehicle)
    return target_vehicle


@router.delete("/vehicles/{license_plate}")
def delete_vehicle(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    # find target vehicle
    target_vehicle = find_vehicle_by_license_plate(license_plate)
    if (
        target_vehicle["user_id"] != session_user["username"]
        and session_user.get("role", "").upper() != "ADMIN"
    ):
        raise HTTPException(status_code=403, detail="Forbidden: cannot delete another users vehicle")
    # performing the deletion
    if not delete_vehicle_from_db(target_vehicle["id"]):
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"status": "Deleted"}


@router.get("/vehicles/{license_plate}/reservations")
def get_vehicle_reservations(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    target_vehicle = find_vehicle_by_license_plate(license_plate)
    if (
        target_vehicle["user_id"] != str(session_user["username"])
        and session_user.get("role", "").upper() != "ADMIN"
    ):
        raise HTTPException(
            status_code=403, detail="Forbidden: cannot access another users vehicle reservations"
        )
    try:
        all_reservations = load_reservation_data_from_db()
    except Exception:
        raise HTTPException(status_code=500, detail="Error loading reservation data")

    vehicle_reservations = [
        reservation
        for reservation in all_reservations
        if reservation.get("vehicle_id") == target_vehicle["id"]
    ]
    return {"reservations": vehicle_reservations}


@router.get("/vehicles/{license_plate}/history")
def get_vehicle_history(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    target_vehicle = find_vehicle_by_license_plate(license_plate)
    if (
        target_vehicle["user_id"] != str(session_user["username"])
        and session_user.get("role", "").upper() != "ADMIN"
    ):
        raise HTTPException(status_code=403, detail="Forbidden, cannot access another users vehicle history")
    from utils.storage_utils import load_parking_lot_data, load_parking_session_data

    parking_lots = load_parking_lot_data()
    completed_sessions = []
    normalized_plate = normalize_plate(license_plate)
    for lot_id, lot_data in parking_lots.items():
        try:
            sessions = load_parking_session_data(lot_id)
            for session_id, session_data in sessions.items():
                if (
                    normalize_plate(session_data.get("licenseplate", "")) == normalized_plate
                    and session_data.get("stopped") is not None
                ):
                    session_with_context = {
                        "session_id": session_id,
                        "parking_lot_id": lot_id,
                        "parking_lot_name": lot_data.get("name"),
                        "parking_lot_address": lot_data.get("address"),
                        **session_data,
                    }
                    completed_sessions.append(session_with_context)
        except FileNotFoundError:
            continue
    completed_sessions.sort(key=lambda x: x.get("stopped", ""), reverse=True)
    return {"history": completed_sessions}
