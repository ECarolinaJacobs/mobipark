from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime
import uuid

from models.vehicles_model import VehicleCreate, VehicleOut
from utils.storage_utils import (
    load_vehicle_data,
    get_vehicle_data_by_id,
    get_vehicle_data_by_user,
    save_new_vehicle_to_db,
    update_existing_vehicle_in_db,
    delete_vehicle_from_db,
    get_user_data_by_username_for_vehicles,
)


from utils.session_manager import get_session


router = APIRouter(tags=["vehicles"])


def normalize_plate(p: str) -> str:
    if not p:
        return ""
    return p.replace("-", "").upper().strip()


def find_vehicle_by_license_plate(
    vehicles: list, license_plate: str, not_found_msg: str = "Vehicle not found"
):
    """Helper function to find a vehicle by lid"""
    lid = normalize_plate(license_plate)
    for v in vehicles:
        if normalize_plate(v["license_plate"]) == lid:
            return v
    raise HTTPException(status_code=404, detail=not_found_msg)


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
    vehicles = load_vehicle_data()

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
    save_new_vehicle_to_db(new_vehicle)
    return new_vehicle


@router.get("/vehicles/{username}", response_model=dict)
@router.get("/vehicles", response_model=dict)
def get_user_vehicles(username: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """
    returns vehicles for the logged in user, if an admin provides a username, returns that users vehicle instead
    """
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    # is username not given, use current users username
    if not username:
        username = session_user["username"]
    # admin check
    if username != session_user["username"] and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied")
    target_user = get_user_data_by_username_for_vehicles(username)
    print(target_user)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_vehicles = get_vehicle_data_by_user(str(target_user["username"]))
    return {"vehicles": user_vehicles}


@router.put("/vehicles/{license_plate}", response_model=VehicleOut)
def update_vehicle(license_plate: str, payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    vehicles = load_vehicle_data()
    print("Lid is " + license_plate.replace("-", "").upper())

    # find the owner for this vehicle
    target_vehicle = find_vehicle_by_license_plate(vehicles, license_plate)
    vehicle_owner = target_vehicle["user_id"]  # stored as username
    logged_in_user = session_user["username"]

    print(f"Owner is {vehicle_owner}")

    # only owner or admin can update
    if logged_in_user != vehicle_owner and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: cannot modify another users vehicle")

    # update fields
    target_vehicle["license_plate"] = payload.license_plate
    target_vehicle["make"] = payload.make
    target_vehicle["model"] = payload.model
    target_vehicle["color"] = payload.color
    target_vehicle["year"] = payload.year

    print("SESSION USER:", session_user)
    print("OWNER USER:", vehicle_owner)

    update_existing_vehicle_in_db(target_vehicle["id"], target_vehicle)

    try:
        return VehicleOut(
            id=target_vehicle["id"],
            user_id=target_vehicle["user_id"],
            license_plate=target_vehicle["license_plate"],
            make=target_vehicle["make"],
            model=target_vehicle["model"],
            color=target_vehicle["color"],
            year=target_vehicle["year"],
            created_at=datetime.fromisoformat(target_vehicle["created_at"]),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal data error: {str(e)}")


@router.delete("/vehicles/{license_plate}")
def delete_vehicle(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_vehicle_data()
    # find target vehicle
    target_vehicle = find_vehicle_by_license_plate(vehicles, license_plate)
    if target_vehicle["user_id"] != str(session_user["username"]) and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: cannot delete another users vehicle")
    # performing the deletion
    success = delete_vehicle_from_db(target_vehicle["id"])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete vehicle")
    return {"status": "Deleted"}


@router.get("/vehicles/{license_plate}/reservations")
def get_vehicle_reservations(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_vehicle_data()

    # find target vehicle
    target_vehicle = find_vehicle_by_license_plate(vehicles, license_plate)
    if target_vehicle["user_id"] != str(session_user["username"]) and session_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403, detail="Forbidden: cannot access another users vehicle reservations"
        )
    # placeholder until reservations integration
    return {"reservations": []}


@router.get("/vehicles/{license_plate}/history")
def get_vehicle_history(license_plate: str, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_vehicle_data()

    target_vehicle = find_vehicle_by_license_plate(vehicles, license_plate)
    if target_vehicle["user_id"] != str(session_user["username"]) and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: cannot access another users vehicle history")
    return {"history": []}
