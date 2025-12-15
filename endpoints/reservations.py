from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from models.reservations_model import CreateReservation, UpdateReservation
import logging
from utils.storage_utils import load_reservation_data, save_reservation_data, load_parking_lot_data, save_parking_lot_data
from utils.session_manager import get_session
from datetime import datetime, timezone
logger = logging.getLogger(__name__)


USER = "USER"
ADMIN = "ADMIN"

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

# --- Helper Functions ---
def find_reservation_by_id(reservations_list: List[Dict[str, Any]], reservation_id: str) -> Optional[Dict[str, Any]]:
    for reservation in reservations_list:
        if reservation.get("id") == reservation_id:
            return reservation
    return None

def find_reservation_index_by_id(reservations_list: List[Dict[str, Any]], reservation_id: str) -> Optional[int]:
    for i, reservation in enumerate(reservations_list):
        if reservation.get("id") == reservation_id:
            return i
    return None

def get_next_reservation_id(reservations_list: List[Dict[str, Any]]) -> str:

    if not reservations_list:
        return "1"
    max_id = 0
    for res in reservations_list:
        try:
            res_id_int = int(res.get("id", 0))
            if res_id_int > max_id:
                max_id = res_id_int
        except (ValueError, TypeError):
            continue
    return str(max_id + 1)


router = APIRouter(
    tags=["reservations"],
    responses={
        200: {"description": "Successfully requested"},
        201: {"description": "Successfully created"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource does not exist"}
    }
)

@router.post("/reservations/")
def create_reservation(reservation_data: CreateReservation, session_user: Dict[str, str] = Depends(require_auth)) -> JSONResponse: 

    try:
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")    
    if reservation_data.parking_lot_id not in parking_lots:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")


    if session_user.get("role") == ADMIN:
        if not reservation_data.user_id:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Required field missing", "field": "user_id"})
    else:
        reservation_data.user_id = session_user["username"]

    rid = get_next_reservation_id(reservations)
    
    reservation_data_dict = reservation_data.model_dump()
    reservation_data_dict["id"] = rid
    reservation_data_dict["created_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat(timespec='seconds').replace('+00:00', 'Z')

    reservations.append(reservation_data_dict)
    
    parking_lot_id = reservation_data.parking_lot_id
    parking_lots[parking_lot_id]["reserved"] += 1
    
    try:
        save_reservation_data(reservations)
        save_parking_lot_data(parking_lots)
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"status": "Success", "reservation": reservation_data_dict})
    
@router.get("/reservations/{reservation_id}")
def get_reservation_by_id(reservation_id: str, session_user: Dict[str, str] = Depends(require_auth)):

    try:
        reservations = load_reservation_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data")
           
    reservation = find_reservation_by_id(reservations, reservation_id)
 
    if reservation:
        if not session_user.get('role') == ADMIN and not session_user["username"] == reservation.get("user_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"reservation": reservation})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

@router.put("/reservations/{reservation_id}")
def update_reservation(reservation_id: str, reservation_data: UpdateReservation, session_user: Dict[str, str] = Depends(require_auth)):

    try:
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")

    reservation_index = find_reservation_index_by_id(reservations, reservation_id)

    if reservation_index is not None:
        old_reservation = reservations[reservation_index]

        if not session_user.get('role') == ADMIN and not session_user["username"] == old_reservation.get("user_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if session_user.get("role") != ADMIN:
            if reservation_data.cost is not None:
                raise HTTPException(
                    status_code=403,
                    detail="Only admins can modify reservation cost"
                )
            if reservation_data.status is not None:
                raise HTTPException(
                    status_code=403,
                    detail="Only admins can modify reservation status"
        )
            
        if session_user.get("role") == ADMIN and reservation_data.status is not None:
            VALID_STATUSES = ["pending", "confirmed", "cancelled"]
            if reservation_data.status not in VALID_STATUSES:
                 raise HTTPException(
                    status_code=403,
                    detail="Invalid status"
                 )

        if session_user.get('role') == ADMIN :
            if not reservation_data.user_id:
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Required field missing", "field": "user_id"})
        else:
            reservation_data.user_id = session_user["username"]

        old_parking_lot_id = old_reservation.get("parking_lot_id")
        new_parking_lot_id = reservation_data.parking_lot_id

        if new_parking_lot_id not in parking_lots:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New parking lot not found")

        if old_parking_lot_id != new_parking_lot_id:
            if old_parking_lot_id in parking_lots:
                parking_lots[old_parking_lot_id]["reserved"] = max(0, parking_lots[old_parking_lot_id]["reserved"] - 1)

            parking_lots[new_parking_lot_id]["reserved"] += 1

        updated_reservation_dict = reservation_data.model_dump()
        updated_reservation_dict["id"] = reservation_id 

        reservations[reservation_index] = updated_reservation_dict

        try:
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")
    
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "Updated", "reservation": updated_reservation_dict})
        
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

@router.delete("/reservations/{reservation_id}")
def delete_reservation(reservation_id: str, session_user: Dict[str, str] = Depends(require_auth)):
    try:
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading parking lot data")
    
    reservation_index = find_reservation_index_by_id(reservations, reservation_id)

    if reservation_index is not None:
        reservation_to_delete = reservations[reservation_index]
        pid = reservation_to_delete.get("parking_lot_id")

        if not session_user.get('role') == ADMIN and not session_user["username"] == reservation_to_delete.get("user_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        del reservations[reservation_index]
        
        if pid in parking_lots:
            parking_lots[pid]["reserved"] = max(0, parking_lots[pid]["reserved"] - 1)
        else:
            logging.warning(f"Reservation {reservation_id} was deleted, but its parking lot {pid} was not found.")
       
        try:
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "Deleted", "id": reservation_id})
    
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")