from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Request, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse, Response
from models.parking_lots_model import ParkingLot, Coordinates, ParkingSessionCreate, UpdateParkingLot

from services import parking_services, auth_services
from utils.storage_utils import (
    save_parking_lot_data,
    load_parking_lot_data,
    save_parking_session_data,
)

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
    """
    Retrieve a specific parking lot.

    Logic:
    1. Loads parking lot by ID.
    """
    parking_lots = load_parking_lot_data()
    lot = next((lot for lot in parking_lots if lot.get("id") == parking_lot_id),
        None)
    if lot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking lot does not exist"
        )
    
    return lot

@router.get(
    "/parking-lots/",
    summary="Retrieve all current parking lots",
    response_description="Parking lot details"
)
def get_parking_lots():
    """
    Retrieve all parking lots.

    Logic:
    1. load parking lot data and return its contents
    """
    parking_lots = load_parking_lot_data()
    return parking_lots

@router.get(
    "/parking-lots/{parking_lot_id}/sessions",
    summary="Retrieve session(s) in a specific parking lot",
    response_description="Parking session details"
)
def get_parking_sessions(parking_lot_id: str, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Retrieve a specific parking lot's sessions.

    Logic:
    1. Verifies session.
    2. Loads parking lot session by a lot's ID.
    3. If user: loads all of the user's sessions in that lot.
       If admin: loads all sessions in that lot.
    """
    return parking_services.get_parking_sessions(parking_lot_id, session_user)
    
@router.post(
    "/parking-lots/",
    summary="Create new parking lot",
    response_description="Parking lot creation"
)
def create_parking_lot(parking_lot: ParkingLot, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Create a parking lot.

    Logic:
    1. Verifies if user is an admin.
    2. Verifies if data matches model.
    3. Saves parking lot to storage.
    """
    auth_services.verify_admin(session_user)
    new_lot = parking_services.create_parking_lot(parking_lot, session_user)

    return JSONResponse(
        content=new_lot,
        status_code=status.HTTP_200_OK
    )

@router.post(
    "/parking-lots/{parking_lot_id}/sessions/start"
)
def start_parking_session(
    parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Start a parking session.

    Logic:
    1. Verifies session.
    2. Verifies if data matches model.
    3. Verifies if parking lot exists.
    4. Checks if there is enough capacity for another session.
    5. Checks if license plate is not already present in parking lot.
    6. Saves parking session to storage.
    """
    started_session = parking_services.start_parking_session(parking_lot_id, session_data, session_user)

    return JSONResponse(
    content=started_session,
    status_code=status.HTTP_200_OK
    )


@router.put(
    "/parking-lots/{parking_lot_id}/sessions/stop"
)
def stop_parking_session(
    parking_lot_id: str,
    session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Stop a parking session.

    Logic:
    1. Verifies if data matches model.
    2. Verifies if parking lot exists.
    3. Verifies session.
    4. Verifies if data matches model.
    5. Verifies if session exists.
    6. Adds cost, duration and payment and payment status.
    7. Saves new parking session data to storage.
    """
    stopped_session = parking_services.stop_parking_session(parking_lot_id, session_data, session_user)
    
    return JSONResponse(
    content=stopped_session,
    status_code=status.HTTP_200_OK
    )

@router.put(
    "/parking-lots/{parking_lot_id}",
    summary="Update parking lot entry data",
    response_description="Update parking lot"
)
def update_parking_lot(
    parking_lot_id: str,
    parking_lot_data: UpdateParkingLot,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)
):
    """
    Update a parking lot.

    Logic:
    1. Verifies if data matches model.
    2. Verifies admin session.
    3. Verifies if parking lot exists.
    4. Saves updated parking lot data to storage.
    """
    auth_services.verify_admin(session_user)
    updated_lot = parking_services.update_parking_lot(parking_lot_id, parking_lot_data)

    return JSONResponse(
        content=updated_lot,
        status_code=status.HTTP_200_OK
    )

@router.put(
    "/parking-lots/{parking_lot_id}/sessions/{parking_session_id}",
    summary="Update parking session entry data",
    response_description="Update parking session"
)
def update_parking_session(
    parking_lot_id: str,
    parking_session_id: str,
    parking_session_data: ParkingSessionCreate,
    session_user: Dict[str, str] = Depends(auth_services.require_auth)
):
    """
    Update a parking session.

    Logic:
    1. Verifies if data matches model.
    2. Verifies admin session.
    3. Verifies if parking lot exists.
    5. Saves updated parking session data to storage.
    """
    auth_services.verify_admin(session_user)
    updated_session = parking_services.update_parking_session(parking_lot_id, parking_session_id, parking_session_data)

    return JSONResponse(
        content=updated_session,
        status_code=status.HTTP_200_OK
    )

@router.delete(
    "/parking-lots/{parking_lot_id}",
    summary="Delete parking lot entry",
    response_description="Deletes a parking lot entry by ID"
)
def delete_parking_lot(parking_lot_id: str, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Delete a parking lot.

    Logic:
    1. Verifies admin session.
    2. Verifies if parking lot exists.
    3. Removes parking lot from storage.
    """
    auth_services.verify_admin(session_user)
    parking_services.delete_parking_lot(parking_lot_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete(
    "/parking-lots/{parking_lot_id}/sessions/{parking_session_id}",
    summary="Delete session entry",
    response_description="Deletes a parking session by ID"
)
def delete_parking_session(parking_session_id: str,
    parking_lot_id: str, 
    session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    """
    Delete a parking session.

    Logic:
    1. Verifies admin session.
    2. Verifies if parking session exists.
    3. Removes parking session from storage.
    """
    auth_services.verify_admin(session_user)
    parking_services.delete_parking_session(parking_session_id, parking_lot_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
