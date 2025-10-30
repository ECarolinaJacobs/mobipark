from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Request, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from models.parking_lots_model import ParkingLot, Coordinates, ParkingSessionCreate

from utils.session_manager import get_session
from utils.storage_utils import (
    save_parking_lot_data,
    load_parking_lot_data,
    save_parking_session_data,
    load_parking_session_data
)

def require_auth(request: Request) -> Dict[str, str]:
    auth_token = request.headers.get("Authorization")
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    session_user = get_session(auth_token)
    
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    
    return session_user

router = APIRouter(
    tags=["parking-lots"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource does not exist"}
    }
)

@router.get(
    "/parking-lots/{parking_lot_id}",
    summary="Retrieve a single parking lot by ID",
    response_description="Parking lot details"
)
def get_parking_lot_by_id(parking_lot_id: str):
    parking_lots = load_parking_lot_data()
    return parking_lots[parking_lot_id]

@router.get(
    "/parking-lots/",
    summary="Retrieve all current parking lots",
    response_description="Parking lot details"
)
def get_parking_lots():
    parking_lots = load_parking_lot_data()
    return parking_lots

@router.get(
    "/parking-lots/{parking_lot_id}/sessions",
    summary="Retrieve session(s) in a specific parking lot",
    response_description="Parking session details"
)
def get_parking_sessions(parking_lot_id: str, session_user: Dict[str, str] = Depends(require_auth)):
    parking_sessions = load_parking_session_data(parking_lot_id)
    sessions_to_display = []

    # TODO: validate parking lots
    if session_user.get("role") != "ADMIN":
        for k, v in parking_sessions.items():
            if v["user"] == session_user.get("username"):
                sessions_to_display.append((k, v))
        return sessions_to_display
    else:
        return parking_sessions
    
@router.post(
    "/parking-lots/",
    summary="Create new parking lot",
    response_description="Parking lot creation"
)
def create_parking_lot(parking_lot: ParkingLot, session_user: Dict[str, str] = Depends(require_auth)):
    if session_user.get("role") != "ADMIN":
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
    
    # TODO: Validate parking lots
    parking_lots = load_parking_lot_data()
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
            parking_lot.coordinates.lat,
            parking_lot.coordinates.lng
        }
    }

    try:
        parking_lots[new_id] = parking_lot_entry
        save_parking_lot_data(parking_lots)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parking lot"
        )
    
    return JSONResponse(
        content=parking_lot_entry,
        status_code=status.HTTP_200_OK
    )

@router.post(
    "/parking-lots/sessions/{parking_lot_id}/start"
)
def start_parking_session(
    parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(require_auth)):

    parking_sessions = load_parking_session_data(parking_lot_id)
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
        save_parking_session_data(parking_sessions, parking_lot_id)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save parking session"
        )

    return JSONResponse(
    content=parking_session_entry,
    status_code=status.HTTP_200_OK
    )


@router.put(
    "/parking-lots/sessions/{parking_lot_id}/stop"
)
def stop_parking_session(
    parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(require_auth)):

    # TODO: Add parking lot ID
    # TODO: Check for valid token
    # TODO: Calculate cost of session
    # TODO: Update payment status
    
    updated_parking_session_entry = None
    parking_sessions = load_parking_session_data(parking_lot_id)
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
        save_parking_session_data(parking_sessions, parking_lot_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update parking session"
        )
    
    return JSONResponse(
    content=updated_parking_session_entry,
    status_code=status.HTTP_200_OK
    )

@router.put(
    "/parking-lots/{parking_lot_id}",
    summary="Update parking lot entry data",
    response_description="Update parking lot"
)
def update_parking_lot(
    parking_lot_id: str,
    parking_lot_data: ParkingLot,
    session_user: Dict[str, str] = Depends(require_auth)
):
    if session_user.get("role") != "ADMIN":
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    parking_lots = load_parking_lot_data()
    if parking_lot_id not in parking_lots:
        raise HTTPException(404, "Parking lot not found")

    updated_lot_encoded = jsonable_encoder(parking_lot_data)
    parking_lots[parking_lot_id].update(updated_lot_encoded)
    
    try:
        save_parking_lot_data(parking_lots)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update parking lot"
        )

    return JSONResponse(
        content=parking_lots[parking_lot_id],
        status_code=status.HTTP_200_OK
    )