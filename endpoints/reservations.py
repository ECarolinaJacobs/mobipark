from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from models.reservations_model import CreateReservation, UpdateReservation
import logging
from utils.storage_utils import (
    load_reservation_data,
    save_reservation_data,
    load_parking_lot_data,
    save_parking_lot_data,
)
from utils.session_manager import get_session
from datetime import datetime

logger = logging.getLogger(__name__)


USER = "USER"
ADMIN = "ADMIN"

# --- Helper Functions ---

def require_auth(request: Request) -> Dict[str, str]:
    auth_token = request.headers.get("Authorization")

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    session_user = get_session(auth_token)

    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token"
        )

    return session_user

def find_earliest_available_time(parking_lot_id: str, reservations: List[Dict[str, Any]]) -> Optional[str]:
    """find the earliest end_time from all active reservations for a specific parking lot
    (returns earliest end_time as string, none if no reservations)"""
    active_reservations = [
        res
        for res in reservations
        if res.get("parking_lot_id") == parking_lot_id
        and res.get("status") in ["pending", "confirmed"]
        and res.get("end_time")
    ]
    if not active_reservations:
        return None
    # parsing all end_times and finding earliest
    earliest_time = None
    for res in active_reservations:
        try:
            end_time = datetime.strptime(res["end_time"], "%Y-%m-%dT%H:%M")
            if earliest_time is None or end_time < earliest_time:
                earliest_time = end_time
        except (ValueError, KeyError):
            continue
    return earliest_time.strftime("%Y-%m-%dT%H:%M") if earliest_time else None


def find_reservation_by_id(
    reservations_list: List[Dict[str, Any]], reservation_id: str
) -> Optional[Dict[str, Any]]:
    for reservation in reservations_list:
        if reservation.get("id") == reservation_id:
            return reservation
    return None


def find_reservation_index_by_id(
    reservations_list: List[Dict[str, Any]], reservation_id: str
) -> Optional[int]:
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
        404: {"description": "Not Found - Resource does not exist"},
    },
)


@router.post(
    "/reservations/",
    summary="Create a reservation",
    description="Create a reservation for a parking lot",
    tags=["reservations"],
    response_description="Succesfully created a reservation",
    responses= {
        500: {"description": "Error loading or saving data"},
        404: {"description": "Parking lor not found"},
        442: {"description": "end_time must be after start_time"},
        409: {"description": "Parking lot is full"}
        }
)
def create_reservation(
    reservation_data: CreateReservation, session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Create a reservation for a parking lot.

    - **Users**: Can only create reservations for themselves.
    - **Admins**: Must provide a user_id to create a reservation for a user.
    - **Validation**: Checks if the lot is full, if start time is before end time and if the required fields are implemented.
    """
    try:
    
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
        if parking_lots is None or reservations is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")
    
    parking_lot = next((lot for lot in parking_lots if lot.get("id") == reservation_data.parking_lot_id), None)

    if parking_lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking lot not found")
    if reservation_data.start_time >= reservation_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_time must be after start_time"
        )

    if parking_lot["reserved"] >= parking_lot["capacity"]:
        earliest_available = find_earliest_available_time(reservation_data.parking_lot_id, reservations)
        if earliest_available:
            try:
                requested_start = datetime.strptime(reservation_data.start_time, "%Y-%m-%dT%H:%M")
                earliest_available_dt = datetime.strptime(earliest_available, "%Y-%m-%dT%H:%M")
                if requested_start < earliest_available_dt:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Parking lot is full. Earliest available time is {earliest_available}",
                    )
            except ValueError as e:
                logging.error(f"Error parsing datetime: {e}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid datetime format")
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parking lot is currently full")

    if session_user.get("role") == ADMIN:
        if not reservation_data.user_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Required field missing", "field": "user_id"},
            )
    else:
        reservation_data.user_id = session_user["username"]

    rid = get_next_reservation_id(reservations)

    reservation_data_dict = reservation_data.model_dump()
    reservation_data_dict["id"] = rid
    reservation_data_dict["created_at"] = (
        datetime.now().replace(microsecond=0).isoformat(timespec="minutes").replace("+00:00", "")
    )

    reservations.append(reservation_data_dict)

    parking_lot["reserved"] += 1

    try:
        save_reservation_data(reservations)
        save_parking_lot_data(parking_lots)
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"status": "Success", "reservation": reservation_data_dict},
    )


@router.get(
    "/reservations/{reservation_id}",
    summary="Retrieve reservation by id",
    description="Retrieve reservation by id",
    tags=["reservations"],
    response_description="Succesfully retrieved reservation",
    responses= {
        500: {"description": "Error loading or saving data"},
        403: {"description": "Access denied"},
        404: {"description": "Reservation not found"}
    }
    )
def get_reservation_by_id(reservation_id: str, session_user: Dict[str, str] = Depends(require_auth)):
    """
    Retrieve a reservation by id.

    -**USERS**: Can only retrieve their own reservation
    -**ADMIN**: Can Retrieve all reservations
    -**Validation**: Looks if the user is allowed to retrieve the reservation data, checks if the reservation exists.
    """
    try:
        reservations = load_reservation_data()
        if reservations is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")
    except Exception as e:
        logging.error(f"Unexpected error when loading reservation data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading reservation data"
        )

    reservation = find_reservation_by_id(reservations, reservation_id)

    if reservation:
        if not session_user.get("role") == ADMIN and not session_user["username"] == reservation.get(
            "user_id"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"reservation": reservation})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")


@router.put(
    "/reservations/{reservation_id}",
    summary="Update a reservation",
    description="Update a reservation by id.",
    tags=["reservations"],
    response_description="Succesfully updated reservation",
    responses= {
        500: {"description": "Error loading or saving data"},
        422: {"description": "end_time must be after start_time"},
        403: {"description": "Access denied"},
        401: {"description": "Required field missing"},
        404: {"description": "Parking lot or reservation not found"},
    }
    )
def update_reservation(
    reservation_id: str,
    reservation_data: UpdateReservation,
    session_user: Dict[str, str] = Depends(require_auth),
):
    """
    Update a reservation by id.

    -**Users**: Can only update their own reservation and cant update the cost or status of the reservation
    -**Admin**: Can update every clients reservation including the cost and status of it
    -**Validation**:
        Checks if the end time is before the start time.
        Checks if the user has permission to update the reservation.
        Denies permission to update the cost and status if its a user and not Admin.
        Checks if the status is valid.
        If the admin updates a reservation, checks if the the user_id is given.
        Checks if the updated parking lot id exists.
        Gives an error if the reservation is not found.
    """
    try:
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
        if parking_lots is None or reservations is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")

    reservation_index = find_reservation_index_by_id(reservations, reservation_id)

    if reservation_index is not None:
        if reservation_data.start_time and reservation_data.end_time:
            if reservation_data.start_time >= reservation_data.end_time:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_time must be after start_time"
                )
        old_reservation = reservations[reservation_index]
        if not session_user.get("role") == ADMIN and not session_user["username"] == old_reservation.get(
            "user_id"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if session_user.get("role") != ADMIN:
            if reservation_data.cost is not None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can modify reservation cost")
            if reservation_data.status is not None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can modify reservation status")

        if session_user.get("role") == ADMIN and reservation_data.status is not None:
            VALID_STATUSES = ["pending", "confirmed", "cancelled"]
            if reservation_data.status not in VALID_STATUSES:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid status")

        if session_user.get("role") == ADMIN:
            if not reservation_data.user_id:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT   ,
                    content={"error": "Required field missing", "field": "user_id"},
                )
        else:
            reservation_data.user_id = session_user["username"]


        old_parking_lot_id = old_reservation.get("parking_lot_id")
        new_parking_lot_id = reservation_data.parking_lot_id

        # Find new parking lot
        new_parking_lot = next((lot for lot in parking_lots if lot.get("id") == new_parking_lot_id), None)
        if new_parking_lot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New parking lot not found")

        if old_parking_lot_id != new_parking_lot_id:
            # Find old parking lot
            old_parking_lot = next((lot for lot in parking_lots if lot.get("id") == old_parking_lot_id), None)
            
            if old_parking_lot:
                old_parking_lot["reserved"] = max(
                    0, old_parking_lot["reserved"] - 1
                )

            new_parking_lot["reserved"] += 1

        updated_reservation_dict = reservation_data.model_dump()
        updated_reservation_dict["id"] = reservation_id

        reservations[reservation_index] = updated_reservation_dict

        try:
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "Updated", "reservation": updated_reservation_dict},
        )

    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")


@router.delete(
    "/reservations/{reservation_id}",
    summary="Delete a reservation.",
    description="Delete a reservation by id.",
    tags=["reservations"],
    response_description="Succesfully removed a reservation",
    responses= {
        500: {"description": "Error loading or saving data"},
        403: {"description": "Access denied"},
        404: {"description": "Reservation not found"},
    }
)
def delete_reservation(reservation_id: str, session_user: Dict[str, str] = Depends(require_auth)):
    """
    Delete a reservation by id.

    -**Users**: Can only delete their own reservation.
    -**Admin**: Can delete every reservation
    -**Validation**:
    Checks if the reservation belongs to the user.
        Checks if the parking lot exists.
        Checks if the reservation exists
    """
    try:
        reservations = load_reservation_data()
        parking_lots = load_parking_lot_data()
        if parking_lots is None or reservations is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading data")
    except Exception as e:
        logging.error(f"Unexpected error when loading data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error loading parking lot data"
        )

    reservation_index = find_reservation_index_by_id(reservations, reservation_id)

    if reservation_index is not None:
        reservation_to_delete = reservations[reservation_index]
        pid = reservation_to_delete.get("parking_lot_id")

        if not session_user.get("role") == ADMIN and not session_user[
            "username"
        ] == reservation_to_delete.get("user_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        del reservations[reservation_index]

        # Find parking lot
        parking_lot = next((lot for lot in parking_lots if lot.get("id") == pid), None)

        if parking_lot:
            parking_lot["reserved"] = max(0, parking_lot["reserved"] - 1)
        else:
            logging.warning(
                f"Reservation {reservation_id} was deleted, but its parking lot {pid} was not found."
            )

        try:
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving data")

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"status": "Deleted", "id": reservation_id}
        )

    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
