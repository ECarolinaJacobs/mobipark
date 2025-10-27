from datetime import datetime

import fastapi
from fastapi import APIRouter, Request, HTTPException, Depends, status

from utils.session_manager import get_session
from utils.storage_utils import (
    save_parking_lot_data,
    load_parking_lot_data
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
    tags=["payments"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource does not exist"}
    }
)

@router.get(
    "/parking-lots/{parkinglot_id}",
    summary="Retrieve a single parking lot by ID",
    response_description="Parking lot details"
)
def get_parking_lot_by_id():
