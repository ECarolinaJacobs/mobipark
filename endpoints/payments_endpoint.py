from typing import List, Dict, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from utils.session_manager import get_session
from utils.storage_utils import (
    load_payment_data,
    save_payment_data,
)
from models.payments_model import PaymentCreate, PaymentUpdate, Payment, TData
from utils.session_calculator import (
    generate_payment_hash,
    generate_transaction_validation_hash
)

# Set up logging
logger = logging.getLogger(__name__)

ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"


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
    "/payments/{payment_id}",
    summary="Get a single payment by ID",
    response_description="Payment details"
)
def get_payment_by_id(
    payment_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    try:
        payments = load_payment_data()
    except Exception as e:
        logger.error(f"Failed to load payment data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load payment data"
        )
    
    # Find the payment
    payment = next(
        (p for p in payments if p["transaction"] == payment_id),
        None
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
    try:
        payments = load_payment_data() or []
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
        # Validate t_data is provided
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
        
        # Load existing payments
        try:
            payments = load_payment_data()
        except FileNotFoundError:
            logger.warning("Payment data file not found, creating new list")
            payments = []
        except Exception as e:
            logger.error(f"Failed to load payment data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load payment data"
            )
        
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
        
        # Persist the payment
        try:
            payments.append(payment)
            save_payment_data(payments)
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
        if payment_update.amount < 0 or payment_update.t_data.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        
        # Load payments
        try:
            payments = load_payment_data()
        except Exception as e:
            logger.error(f"Failed to load payment data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load payment data"
            )
        
        # Find the payment by transaction ID
        payment_index = None
        for i, payment in enumerate(payments):
            if payment["transaction"] == payment_id:
                payment_index = i
                break
        
        if payment_index is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with transaction id {payment_id} not found"
            )
        
        # Get the existing payment
        payment = payments[payment_index]
        
        # Apply partial update (only fields that were explicitly set)
        update_data = payment_update.model_dump(exclude_unset=True)
        
        # Handle nested t_data update
        if "t_data" in update_data and update_data["t_data"]:
            if "t_data" not in payment:
                payment["t_data"] = {}
            payment["t_data"].update(update_data["t_data"])
            del update_data["t_data"]
        
        # Convert session_id and parking_lot_id to strings if present
        if "session_id" in update_data:
            update_data["session_id"] = str(update_data["session_id"])
        if "parking_lot_id" in update_data:
            update_data["parking_lot_id"] = str(update_data["parking_lot_id"])
        
        # Update other fields
        payment.update(update_data)
        
        # Persist changes
        try:
            payments[payment_index] = payment
            save_payment_data(payments)
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


def get_payment_by_transaction_id(
    transaction_id: str,
    payments: Optional[List[Dict]] = None
) -> Optional[Dict]:
    if payments is None:
        payments = load_payment_data()
    
    return next(
        (p for p in payments if p["transaction"] == transaction_id),
        None
    )


def filter_payments_by_user(
    payments: List[Dict],
    username: str
) -> List[Dict]:
    return [p for p in payments if p["initiator"] == username]