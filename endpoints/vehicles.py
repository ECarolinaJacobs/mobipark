from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime

from models.vehicles_endpoints import VehicleCreate, VehicleOut
from utils.storage_utils import load_json, save_data
from utils.session_manager import get_session

router = APIRouter(tags=["vehicles"])

# use this path for testing
DATA_PATH = "data/vehicles_converted.json"
# DATA_PATH = "data/vehicles.json"


@router.post("/vehicles", response_model=VehicleOut)
def create_vehicle(payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    uvehicles = vehicles.get(session_user["username"], {})

    lid = payload.license_plate.replace("-", "").upper()
    if lid in uvehicles:
        raise HTTPException(status_code=400, detail="Vehicle already exists")
    new_vehicle = VehicleOut(
        license_plate=payload.license_plate,
        name=payload.name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    if not uvehicles:
        vehicles[session_user["username"]] = {}
    vehicles[session_user["username"]][lid] = {
        **new_vehicle.model_dump(),
        "created_at": new_vehicle.created_at.isoformat(),
        "updated_at": new_vehicle.updated_at.isoformat(),
    }

    save_data(DATA_PATH, vehicles)
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
    vehicles = load_json(DATA_PATH)
    # if is admin and requested another users data
    if username:
        if session_user.get("role") != "ADMIN":
            raise HTTPException(status_code=403, detail="Access denied")
        if username not in vehicles:
            raise HTTPException(status_code=404, detail="User not found")
        return vehicles.get(username, {})
    # normal user
    return vehicles.get(session_user["username"], {})


@router.put("/vehicles/{license_plate}", response_model=VehicleOut)
def update_vehicle(license_plate: str, payload: VehicleCreate, authorization: Optional[str] = Header(None)):
    token = authorization
    if not token or not get_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_user = get_session(token)
    vehicles = load_json(DATA_PATH)
    lid = license_plate.replace("-", "").upper()
    print("Lid initial is" + lid)

    # find the owner for this vehicle
    owner_username = None
    for username, user_vehicles in vehicles.items():
        normalized_keys = {k.upper(): k for k in user_vehicles.keys()}
        if lid in normalized_keys:
            owner_username = username
            lid = normalized_keys[lid]
            break

    if not owner_username:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    print(f"Owner is {owner_username}")
    print("Lid changed is" + lid)

    if owner_username != session_user["username"] and session_user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden: cannot modify another user's vehicle")
    vehicle = vehicles[owner_username][lid]
    vehicle["name"] = payload.name
    vehicle["license_plate"] = payload.license_plate
    vehicle["updated_at"] = datetime.now().isoformat()
    print("SESSION USER:", session_user)
    print("OWNER USER:", owner_username)

    save_data(DATA_PATH, vehicles)
    try:
        return VehicleOut(
            license_plate=vehicle.get("license_plate"),
            name=vehicle.get("name"),
            created_at=datetime.fromisoformat(vehicle.get("created_at")),
            updated_at=datetime.fromisoformat(vehicle.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal data error: {str(e)}")


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

    lid = license_plate.replace("-", "").upper()
    if lid not in uvehicles:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"history": []}  # probably a placeholder until sessions or billig module integration
