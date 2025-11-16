from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from models.reservations_model import CreateReservation, UpdateReservation

from utils.storage_utils import load_reservation_data,save_reservation_data,load_parking_lot_data, save_parking_lot_data
from utils.session_manager import get_session

import logging

#You can log unexpected errors to debug 
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


#documentation: "tags" groups the endpoints as reservations
#documentation: "responses" describes the responses that the endpoints might return
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
def create_reservation(reservation_data: CreateReservation,session_user: Dict[str, str] = Depends(require_auth)) -> JSONResponse: 
        
    try:
        reservations = load_reservation_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data")
    
    try:
        parking_lots = load_parking_lot_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading parking lot data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading parking lot data")
    
    rid = str(len(reservations) + 1)

    if reservation_data.parking_lot_id not in parking_lots:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")

    if session_user.get("role") == ADMIN:
        if not reservation_data.user:
            raise JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Required field missing", "field": "user"})
        
    else:
        reservation_data_dict = reservation_data.model_dump()
        reservation_data_dict["id"] = rid
        reservation_data.user = session_user["username"]
        
        reservations.append(reservation_data_dict)
        
        parking_lot_id = reservation_data.parking_lot_id
        parking_lots[parking_lot_id]["reserved"] += 1
       
        save_reservation_data(reservations)
        save_parking_lot_data(parking_lots)

        return JSONResponse(status_code=status.HTTP_201_CREATED, content={"status": "Success", "reservation": reservation_data})
    
@router.get("/reservations/{reservation_id}",)
def get_reservation_by_id(reservation_id: str, session_user: Dict[str,str] = Depends(require_auth)):

    try:
        reservations = load_reservation_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data")
           


 
    if reservation_id in reservations:
        if not session_user.get('role') == ADMIN and not session_user["username"] == reservations[reservation_id].get("user"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Access denied")
        
        reservations[reservation_id]["id"] = reservation_id
        save_reservation_data(reservations)
        
        return JSONResponse(status_code= status.HTTP_200_OK, content={"reservation": reservations[reservation_id]})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    
            

@router.put("/reservations/{reservation_id}",)
def update_reservation(reservation_id: str ,reservation_data: UpdateReservation, session_user : Dict[str, str] = Depends(require_auth)):

    try:
        reservations = load_reservation_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data")


    if reservation_id in reservations:
        
        if session_user.get("role") == ADMIN:
            if not reservation_data.user:
                return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error" : "Required field missing" ,"field": "user"})
        else:
            reservation_data.user = session_user["username"]
            reservations[reservation_id] = reservation_data.model_dump()

            save_reservation_data(reservations)
    
            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "Updated", "reservation": reservation_data})
        
    else:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = "Reservation not found")


@router.delete("/reservations/{reservation_id}")
def delete_reservation(reservation_id: str, session_user: Dict[str,str] = Depends(require_auth) ):
    try:
        reservations = load_reservation_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data")
    
    try:
        parking_lots = load_parking_lot_data()
    except Exception as e:
        logging.error(f"Unexpected error when loading parking lot data: {e}")
        raise HTTPException(status_code =status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading parking lot data")
    

    if reservation_id in reservations:
        pid = reservations[reservation_id]["parking_lot_id"]
        if  session_user.get('role') == ADMIN or session_user["username"] == reservations[reservation_id].get("user"):
            del reservations[reservation_id]
            parking_lots[pid]["reserved"] -= 1
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Access denied")
    
       
        save_reservation_data(reservations)
        save_parking_lot_data(parking_lots)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "Deleted", "id": reservation_id})
    
    else:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
      


