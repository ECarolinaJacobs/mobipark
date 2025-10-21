from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from utils.session_manager import get_session
from utils.storage_utils import (
    load_payment_data,
    save_payment_data,
)
from models.payments_model import PaymentCreate, PaymentUpdate
from utils.session_calculator import (
    generate_payment_hash,
    generate_transaction_validation_hash
)

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
    "/payment/{payment_id}",
    summary="Get a single payment by ID",
    response_description="Payment details"
)
def get_payment_by_id(
    payment_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    payments = load_payment_data()
    
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
    "/payment",
    summary="Get all payments",
    response_description="List of payments"
)
def get_all_payments(
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    payments = load_payment_data() or []
    
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
    "/payment",
    summary="Create a new payment",
    response_description="Created payment details",
    status_code=status.HTTP_201_CREATED
)
def create_payment(
    payment_create: PaymentCreate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    payments = load_payment_data()
    
    # Get current timestamp
    now = datetime.now()
    
    # Build the payment object
    payment = {
        "transaction": generate_transaction_validation_hash(),
        "amount": payment_create.amount,
        "initiator": session_user["username"],
        "created_at": now.strftime("%d-%m-%Y %H:%M:%S%s"),
        "completed": payment_create.completed,
        "hash": generate_payment_hash(),
        "t_data": {
            "amount": payment_create.amount,
            "date": payment_create.t_data_date,
            "method": payment_create.t_data_method,
            "issuer": payment_create.t_data_issuer,
            "bank": payment_create.t_data_bank
        },
        "session_id": payment_create.session_id,
        "parking_lot_id": payment_create.parking_lot_id
    }
    
    # Persist the payment
    payments.append(payment)
    save_payment_data(payments)
    
    return JSONResponse(
        content=payment,
        status_code=status.HTTP_201_CREATED
    )


@router.put(
    "/payment/{payment_id}",
    summary="Update an existing payment",
    response_description="Updated payment details"
)
def update_payment(
    payment_id: str,
    payment_update: PaymentUpdate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    if (session_user["role"] != ROLE_ADMIN):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permissions to update payments")
    
    payments = load_payment_data()
    
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
    payment.update(update_data)
    
    # Persist changes
    payments[payment_index] = payment
    save_payment_data(payments)
    
    return JSONResponse(content=payment, status_code=status.HTTP_200_OK)


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