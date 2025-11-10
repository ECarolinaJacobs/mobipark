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
    load_parking_session_data
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
    parking_lots = load_parking_lot_data()
    if parking_lot_id not in parking_lots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking lot does not exist"
        )
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
def get_parking_sessions(parking_lot_id: str, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
    return parking_services.get_parking_session(parking_lot_id, session_user)
    
@router.post(
    "/parking-lots/",
    summary="Create new parking lot",
    response_description="Parking lot creation"
)
def create_parking_lot(parking_lot: ParkingLot, session_user: Dict[str, str] = Depends(auth_services.require_auth)):
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
    auth_services.verify_admin(session_user)
    parking_services.delete_parking_session(parking_session_id, parking_lot_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
