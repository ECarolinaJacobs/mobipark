from typing import List, Dict, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from utils.session_manager import get_session
from utils.storage_utils import (
    # Updated imports for targeted DB functions
    load_payment_data_from_db, 
    get_payment_data_by_id, 
    save_new_payment_to_db, 
    update_existing_payment_in_db
)
from models.payments_model import PaymentCreate, PaymentUpdate
from utils.session_calculator import (
    generate_payment_hash,
    generate_transaction_validation_hash
)

# Set up logging
logger = logging.getLogger(__name__)

ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"


def require_auth(request: Request) -> Dict[str, str]:
    # ... (Authentication remains the same)
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
    "/payments/{payment_id}",
    summary="Get a single payment by ID",
    response_description="Payment details"
)
def get_payment_by_id(
    payment_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    try:
        # OPTIMIZATION: Load only the single payment by ID
        payment = get_payment_data_by_id(payment_id)
    except Exception as e:
        logger.error(f"Failed to load payment data: {e}")
        # The storage_utils will raise an exception if the table query fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load payment data"
        )
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with transaction id {payment_id} not found"
        )
    
    # Authorization check: users can only see their own payments
    is_owner = payment["initiator"] == session_user["username"]
    is_admin = session_user["role"] == ROLE_ADMIN
    
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access payments that are not your own"
        )
    
    return JSONResponse(content=payment, status_code=status.HTTP_200_OK)


@router.get(
    "/payments",
    summary="Get all payments",
    response_description="List of payments"
)
def get_all_payments(
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    # This endpoint still needs to load ALL payments for filtering/admin view
    try:
        payments = load_payment_data_from_db() or []
    except Exception as e:
        logger.error(f"Failed to load payment data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load payment data"
        )
    
    # Admins see all payments
    if session_user["role"] == ROLE_ADMIN:
        return JSONResponse(content=payments, status_code=status.HTTP_200_OK)
    
    # Regular users see only their own payments
    # NOTE: For further optimization, a SQL 'WHERE' clause could be added
    # in storage_utils to filter in the DB before load, but we keep the current
    # list comprehension logic for now as it's simple and load_payment_data_from_db
    # is already optimized to not load all rows into memory at once (via cursor iteration).
    user_payments = [
        p for p in payments 
        if p["initiator"] == session_user["username"]
    ]
    
    return JSONResponse(content=user_payments, status_code=status.HTTP_200_OK)


@router.post(
    "/payments",
    summary="Create a new payment",
    response_description="Created payment details",
    status_code=status.HTTP_201_CREATED
)
def create_payment(
    payment_create: PaymentCreate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    try:
        # ... (Validation remains the same)
        if not payment_create.t_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction data (t_data) is required"
            )
        if payment_create.amount < 0 or payment_create.t_data.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        
        # Load existing payments section REMOVED. No need to load all data.
        
        # Get current timestamp
        now = datetime.now()
        timestamp = int(now.timestamp())
        
        # Generate hashes
        try:
            transaction_hash = generate_transaction_validation_hash()
            payment_hash = generate_payment_hash()
        except Exception as e:
            logger.error(f"Failed to generate hashes: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate payment identifiers"
            )
        
        # Build the payment object
        payment = {
            "transaction": transaction_hash,
            "amount": payment_create.amount,
            "initiator": session_user["username"],
            "created_at": f"{now.strftime('%d-%m-%Y %H:%M:%S')}{timestamp}",
            "completed": payment_create.completed or f"{now.strftime('%d-%m-%Y %H:%M:%S')}{timestamp}",
            "hash": payment_hash,
            "t_data": {
                "amount": payment_create.t_data.amount,
                "date": payment_create.t_data.date,
                "method": payment_create.t_data.method,
                "issuer": payment_create.t_data.issuer,
                "bank": payment_create.t_data.bank
            },
            "session_id": str(payment_create.session_id),
            "parking_lot_id": str(payment_create.parking_lot_id)
        }
        
        # OPTIMIZATION: Persist the single new payment directly
        try:
            save_new_payment_to_db(payment)
        except Exception as e:
            logger.error(f"Failed to save payment: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save payment"
            )
        
        logger.info(f"Payment created: {transaction_hash} by {session_user['username']}")
        
        return JSONResponse(
            content=payment,
            status_code=status.HTTP_201_CREATED
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.put(
    "/payments/{payment_id}",
    summary="Update an existing payment",
    response_description="Updated payment details"
)
def update_payment(
    payment_id: str,
    payment_update: PaymentUpdate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    try:
        # Check admin permission
        if session_user["role"] != ROLE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permissions to update payments"
            )
            
        # OPTIMIZATION: Load only the payment to be updated
        try:
            payment = get_payment_data_by_id(payment_id)
        except Exception as e:
            logger.error(f"Failed to load payment data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load payment data"
            )
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with transaction id {payment_id} not found"
            )
        
        # Apply partial update (only fields that were explicitly set)
        update_data = payment_update.model_dump(exclude_unset=True)
        
        # Handle nested t_data update
        if "t_data" in update_data and update_data["t_data"]:
            if "t_data" not in payment:
                payment["t_data"] = {}
            # Ensure we update the dictionary in the payment object, not overwrite it
            payment["t_data"].update(update_data["t_data"])
            del update_data["t_data"]
        
        # Convert session_id and parking_lot_id to strings if present
        if "session_id" in update_data:
            update_data["session_id"] = str(update_data["session_id"])
        if "parking_lot_id" in update_data:
            update_data["parking_lot_id"] = str(update_data["parking_lot_id"])
        
        # Update other fields in the existing payment object
        payment.update(update_data)
        
        # OPTIMIZATION: Persist the single updated payment directly
        try:
            update_existing_payment_in_db(payment_id, payment)
        except Exception as e:
            logger.error(f"Failed to save payment update: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save payment update"
            )
        
        logger.info(f"Payment updated: {payment_id} by {session_user['username']}")
        
        return JSONResponse(content=payment, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

# NOTE: The helper functions get_payment_by_transaction_id and filter_payments_by_user
# are now redundant or can be simplified as their logic is integrated/moved to storage_utils.