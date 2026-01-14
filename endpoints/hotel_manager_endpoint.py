from typing import Dict
from datetime import datetime
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from utils.session_manager import get_session
from utils.storage_utils import (
    load_parking_lot_data,
    get_discount_by_code,
    save_new_discount_to_db,
    load_discounts_data_from_db,
    update_existing_discount_in_db,
)
from models.hotel_manager_model import HotelDiscountCodeCreate

logger = logging.getLogger(__name__)

ROLE_HOTEL_MANAGER = "HOTEL_MANAGER"
ROLE_ADMIN = "ADMIN"


def require_auth(request: Request) -> Dict[str, str]:
    """Authentication dependency
    :param: request containing auth header
    :return: dict with authenticated user's session data
    """
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    session_user = get_session(auth_token)
    if not session_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token"
        )
    return session_user


def require_hotel_manager(request: Request) -> Dict[str, str]:
    """Hotel manager authentication dependency
    :param request: request obect with auth header
    :return: dictionary with authenticated hotel manager's session data
    """
    session_user = require_auth(request)
    if session_user["role"] != ROLE_HOTEL_MANAGER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hotel manager privileges required")
    if not session_user.get("managed_parking_lot_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No parking lot assigned to this hotel manager"
        )
    return session_user


router = APIRouter(
    prefix="/hotel-manager",
    tags=["hotel-manager"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource does not exist"},
    },
)


@router.post(
    "/discount-codes",
    summary="Create a 100% discount code for hotel guests (Hotel manager only)",
    response_description="Created discount code details",
    status_code=status.HTTP_201_CREATED,
)
def create_hotel_discount_code(
    discount_create: HotelDiscountCodeCreate, session_user: Dict[str, str] = Depends(require_hotel_manager)
) -> JSONResponse:
    """hotel managers can create 100% discount codes for their guests,
    these are only valid for the parking lots they manage
    :param discount_create: discount code creation data
    :param session_user: authenticated hotel manager's session data
    :return: jsonresponse with created discount code details
    """
    try:
        parking_lots = load_parking_lot_data()
        managed_lot_id = session_user["managed_parking_lot_id"]
        if isinstance(parking_lots, dict):
            lot_exists = managed_lot_id in parking_lots
        else:
            lot_exists = any(lot.get("id") == managed_lot_id for lot in parking_lots)
        if not lot_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Managed parking lot {managed_lot_id} not found",
            )

        existing_discount = get_discount_by_code(discount_create.code)
        if existing_discount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Discount code '{discount_create.code}' already exists",
            )
        now = datetime.now()
        timestamp = int(now.timestamp())
        check_in = datetime.fromisoformat(discount_create.check_in_date)
        if check_in.date() < now.date():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Check-in date cannot be in the past",
            )

        # build the hotel discount code object
        discount_code = {
            "code": discount_create.code,
            "discount_type": "percentage",
            "discount_value": 100.0,
            "max_uses": 1,
            "current_uses": 0,
            "active": True,
            "created_at": f"{now.strftime('%d-%m-%Y %H:%M:%S')}{timestamp}",
            "check_in_date": discount_create.check_in_date,
            "check_out_date": discount_create.check_out_date,
            "parking_lot_id": managed_lot_id,
            "created_by": session_user["username"],
            "guest_name": discount_create.guest_name,
            "notes": discount_create.notes,
            "is_hotel_code": 1,
        }
        # save the discount code
        try:
            save_new_discount_to_db(discount_code)

        except Exception as e:
            logger.error(f"Failed to save hotel discount code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save discount code"
            )
        logger.info(
            f"Hotel discount code created: {discount_create.code} "
            f"by {session_user['username']} for parking lot {managed_lot_id} "
            f"(valid from {discount_create.check_in_date} to {discount_create.check_out_date})"
        )
        return JSONResponse(content=discount_code, status_code=status.HTTP_201_CREATED)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_hotel_discount_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.get(
    "/discount-codes",
    summary="Get all discount codes created by this hotel manager",
    response_description="List of hotel discount codes",
)
def get_hotel_discount_codes(session_user: Dict[str, str] = Depends(require_hotel_manager)) -> JSONResponse:
    """returns all discount codes created by the authenticated hotel manager for their parking lot
    :param session_user: authenticated hotel manager's session data
    :return: jsonResponse with list of discount codes created by this hotel manager
    """
    try:
        all_discount_codes = load_discounts_data_from_db() or []
        hotel_codes = [
            code
            for code in all_discount_codes
            if code.get("created_by") == session_user["username"] and code.get("is_hotel_code")
        ]
        return JSONResponse(content=hotel_codes, status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Failed to load hotel discount codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load discount codes"
        )


@router.get(
    "/discount-codes/{code}",
    summary="Get a specific discount code by code",
    response_description="Discount code details",
)
def get_hotel_discount_code_by_code(
    code: str, session_user: Dict[str, str] = Depends(require_hotel_manager)
) -> JSONResponse:
    """returns details of a specific discount code if it was created by this hotel manager
    :param code: the discount code to retrieve
    :param session_user: authenticated hotel manager's session data
    :return: jsonResponse containing the discount code details
    """
    try:
        discount_code = get_discount_by_code(code)
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Discount code '{code}' not found"
            )
        if discount_code.get("created_by") != session_user["username"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You can only view discount codes you created"
            )
        return JSONResponse(content=discount_code, status_code=status.HTTP_200_OK)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_hotel_discount_code_by_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.delete(
    "/discount-codes/{code}",
    summary="Deactivate a hotel discount code",
    response_description="Deactivated discount code details",
)
def deactivate_hotel_discount_code(
    code: str, session_user: Dict[str, str] = Depends(require_hotel_manager)
) -> JSONResponse:
    """deactivates a discount code created by this hotel manager
    :param code: the discount code to deactivate
    :param session_user: authenticated hotel manager's session data
    :return: jsonResponse containing the updated discount code details
    """
    try:
        existing_discount = get_discount_by_code(code)
        if not existing_discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Discount code '{code}' not found"
            )
        if existing_discount.get("created_by") != session_user["username"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only deactivate discount codes you created",
            )
        updated_discount = existing_discount.copy()
        updated_discount["active"] = False
        try:
            update_existing_discount_in_db(code, updated_discount)
        except Exception as e:
            logger.error(f"Failed to deactivate hotel discount code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to deactivate discount code"
            )
        logger.info(f"Hotel discount code deactivated: {code} by {session_user['username']}")
        return JSONResponse(content=updated_discount, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in deactivate_hotel_discount_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred"
        )


@router.get(
    "/managed-parking-lot",
    summary="Get details of the parking lot managed by this hotel manager",
    response_description="Parking lot details",
)
def get_managed_parking_lot(session_user: Dict[str, str] = Depends(require_hotel_manager)) -> JSONResponse:
    """returns details of the parking lot assigned to this hotel manager
    :param session_user: authenticated hotel manager's session data
    :return: jsonResponse containing the managed parking lot details with id included
    """
    try:
        parking_lots = load_parking_lot_data()
        managed_lot_id = session_user["managed_parking_lot_id"]
        if isinstance(parking_lots, dict):
            if managed_lot_id not in parking_lots:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Managed parking lot {managed_lot_id} not found",
                )

            parking_lot = parking_lots[managed_lot_id]
            parking_lot["id"] = managed_lot_id
        else:
            parking_lot = next((lot for lot in parking_lots if lot.get("id") == managed_lot_id), None)
            if not parking_lot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Managed parking lot {managed_lot_id} not found",
                )
        return JSONResponse(content=parking_lot, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load managed parking lot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load parking lot details"
        )
