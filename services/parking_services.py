from datetime import datetime
from typing import Dict

from fastapi import HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder

from models.parking_lots_model import ParkingLot, ParkingSessionCreate
from services import auth_services
from utils import storage_utils

def create_parking_lot(parking_lot: ParkingLot, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    parking_lots = storage_utils.load_parking_lot_data()

    new_id = None
    if parking_lots:
        new_id = str(max(int(k) for k in parking_lots.keys()) + 1)
    else: new_id = "1"

    parking_lot_entry = {
        "name": parking_lot.name,
        "location": parking_lot.location,
        "address": parking_lot.address,
        "capacity": parking_lot.capacity,
        "reserved": parking_lot.reserved,
        "tariff": parking_lot.tariff,
        "daytariff": parking_lot.daytariff,
        "created_at": parking_lot.created_at,
        "coordinates": {
            "lat": parking_lot.coordinates.lat,
            "lng":parking_lot.coordinates.lng
        }
    }

    try:
        parking_lots[new_id] = parking_lot_entry
        storage_utils.save_parking_lot_data(parking_lots)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parking lot"
        )
    
    return parking_lots[new_id]

def update_parking_lot(parking_lot_id: str, parking_lot_data: ParkingLot):
    parking_lots = storage_utils.load_parking_lot_data()
    if parking_lot_id not in parking_lots:
        raise HTTPException(404, "Parking lot not found")
    
    updated_lot_encoded = jsonable_encoder(parking_lot_data)
    parking_lots[parking_lot_id].update(updated_lot_encoded)
    
    try:
        storage_utils.save_parking_lot_data(parking_lots)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update parking lot"
        )
    
    return parking_lots[parking_lot_id]

def start_parking_session(
    parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)
    ):
    parking_sessions = storage_utils.load_parking_session_data(parking_lot_id)
    for key, session in parking_sessions:
        if session["licenseplate"] == session_data.licenseplate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A session for this license plate already exists."
            )

    new_id = None
    if parking_sessions:
        new_id = str(max(int(k) for k in parking_sessions.keys()) + 1)
    else: new_id = "1"

    parking_session_entry = {
        "licenseplate": session_data.licenseplate,
        "started": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "stopped": None,
        "user": session_user.get("username")
    }

    try:
        parking_sessions[new_id] = parking_session_entry
        storage_utils.save_parking_session_data(parking_sessions, parking_lot_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parking session"
        )
    
    return parking_sessions[new_id]

def stop_parking_session(parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    # TODO: Add parking lot ID
    # TODO: Check for valid token
    # TODO: Calculate cost of session
    # TODO: Update payment status
    # TODO: Search by session id, rather than username
    
    updated_parking_session_entry = None
    parking_sessions = storage_utils.load_parking_session_data(parking_lot_id)
    for key, session in parking_sessions.items():
        if session["licenseplate"] == session_data.licenseplate:

            if session["user"] != session_user.get("username") and session_user.get("role") != "ADMIN":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized - invalid or missing session token"
                )

            start_time = datetime.strptime(session["started"], "%d-%m-%Y %H:%M:%S")
            stop_time = datetime.now()
            duration = stop_time - start_time
            # Check if duration in minutes should be rounded up or down
            duration_minutes = int(duration.total_seconds() / 60)

            updated_parking_session_entry = {
                "licenseplate": session_data.licenseplate,
                "started": session["started"],
                "stopped": stop_time.strftime("%d-%m-%Y %H:%M:%S"),
                "user": session["user"],
                "duration_minutes": duration_minutes,
                # Cost should be calculated using calculate_price from session_calculator.py
                "cost": 0,
                # Payment status should be updated through Payment endpoint (probably)
                "payment_status": "Pending"
            }
            parking_sessions[key] = updated_parking_session_entry
            break
    if updated_parking_session_entry == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found - Resource does not exist"
        )

    try:
        storage_utils.save_parking_session_data(parking_sessions, parking_lot_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update parking session"
        )
    
    return updated_parking_session_entry

def get_parking_session(parking_lot_id: str, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    parking_sessions = storage_utils.load_parking_session_data(parking_lot_id)
    user_sessions = {}

    if session_user.get("role") != "ADMIN":
        for k, v in parking_sessions.items():
            if v["user"] == session_user.get("username"):
                user_sessions[k] = v
        return user_sessions
    else:
        return parking_sessions
    
def delete_parking_lot(parking_lot_id: str):
    parking_lots = storage_utils.load_parking_lot_data()

    if parking_lot_id not in parking_lots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found - Resource does not exist"
        )

    parking_lots.pop(parking_lot_id)
    try:
        storage_utils.save_parking_lot_data(parking_lots)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete parking lot"
        )

def delete_parking_session(parking_session_id: str, parking_lot_id: str):
    parking_sessions = storage_utils.load_parking_session_data(parking_lot_id)

    if parking_session_id not in parking_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found - Resource does not exist"
        )
    
    parking_sessions.pop(parking_lot_id)
    try:
        storage_utils.save_parking_session_data(parking_sessions, parking_lot_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete parking session"
        )