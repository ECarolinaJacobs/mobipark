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
    save_vehicle_data_to_db,
    load_reservation_data_from_db,
    load_parking_sessions_data_from_db,
)
from utils.session_manager import get_session


router = APIRouter(tags=["vehicles"])


def normalize_plate(p: str) -> str:
    """Normalize a license plate by removing dashes, converting to uppercase and stripping whitespaces."""
    if not p:
        return ""
    return p.replace("-", "").upper().strip()


def find_vehicle_by_license_plate(license_plate: str):
    """Find a vehicle by it's license plate"""
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
    """
    Create a new vehicle for the authenticated user
    :param payload: vehicle data
    :param authorization: authentication token from request header
    :returns: created vehicle object with generated Id and timestamp
    """
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
        save_vehicle_data_to_db(new_vehicle)
    except Exception:
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    return new_vehicle


@router.get("/vehicles/{username}", response_model=dict)
@router.get("/vehicles", response_model=dict)
def get_user_vehicles(username: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Get all vehicles for a specific user or the authenticated user
    :param username: optional username for retrieving vehicles
    :param authorization: authentication token from request header
    :returns: dictionary containing list of vehicles
    """
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
    """
    Update an existing vehicle's information
    :param license_plate: license plate of vehicle to update
    :param payload: updated vehicle data
    :param authorization: authentication token from request header
    :return: updated vehicle object
    """
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
    """
    Delete a vehicle by it's license plate
    :param license_plate: license plate of the vehicle to delete
    :param authorization: authentication token from request header
    :returns: dictionary with deletion status
    """
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
    """
    Get all reservations for a specific vehicle
    :param license_plate: license plate of the vehicle
    :param authorization: authentication token from request header
    :return: dict containing list of reservations for the vehicle
    """
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
    """
    Get the parking session history for a specific vehicle
    :param license_plate: Description
    :param authorization: Description
    :return: dict containing list of completed parking sessions with parking lot.
    """
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    target_vehicle = find_vehicle_by_license_plate(license_plate)
    if (
        target_vehicle["user_id"] != str(session_user["username"])
        and session_user.get("role", "").upper() != "ADMIN"
    ):
        raise HTTPException(status_code=403, detail="Forbidden, cannot access another users vehicles history")
    from utils.storage_utils import load_parking_lot_data

    parking_lots = load_parking_lot_data()
    completed_sessions = []
    normalized_plate = normalize_plate(license_plate)
    sessions = load_parking_sessions_data_from_db()
    for session in sessions:
        if (
            normalize_plate(session.get("licenseplate", "")) == normalized_plate
            and session.get("stopped") is not None
        ):
            lot_id = session.get("parking_lot_id")
            lot_data = parking_lots.get(lot_id, {}) if lot_id else {}
            session_with_context = {
                "session_id": session["id"],
                "parking_lot_id": lot_id,
                "parking_lot_name": lot_data.get("name"),
                "parking_lot_address": lot_data.get("address"),
                **session,
            }
            completed_sessions.append(session_with_context)
    completed_sessions.sort(key=lambda x: x.get("stopped", ""), reverse=True)
    return {"history": completed_sessions}
