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
    update_existing_payment_in_db,
    get_discount_by_code,
    update_existing_discount_in_db,
    get_payments_by_initiator
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
    """
    Middleware-like dependency to ensure the user is authenticated.
    
    Checks the 'Authorization' header for a valid session token.
    Returns the session user object if valid, raises HTTPException otherwise.
    
    Args:
        request: The incoming HTTP request.
        
    Returns:
        Dict[str, str]: The session user data.
    """
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
    description="Retrieve detailed information about a specific payment transaction. Users can only access their own payments.",
    response_description="Payment details object",
    response_model=Dict,
    status_code=status.HTTP_200_OK
)
def get_payment_by_id(
    payment_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Fetch a payment by its unique transaction ID.
    
    Logic:
    1. Validates the user session.
    2. Loads the payment from the database.
    3. Enforces ownership check: User must be the 'initiator' OR an 'ADMIN'.
    """
    try:
        # OPTIMIZATION: Load only the single payment by ID to avoid reading the whole table
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
    description="Retrieve a list of payments. Admins see all payments; regular users see only their own.",
    response_description="List of payment objects",
    response_model=List[Dict],
    status_code=status.HTTP_200_OK
)
def get_all_payments(
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Fetch all payments accessible to the current user.
    
    Logic:
    1. If ADMIN: Load and return ALL payments.
    2. If USER: Query only payments where 'initiator' matches username.
    """
    try:
        # Admins see all payments
        if session_user["role"] == ROLE_ADMIN:
            payments = load_payment_data_from_db() or []
            return JSONResponse(content=payments, status_code=status.HTTP_200_OK)
        
        # Regular users see only their own payments - Optimized DB query
        user_payments = get_payments_by_initiator(session_user["username"]) or []
        return JSONResponse(content=user_payments, status_code=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to load payment data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load payment data"
        )


@router.post(
    "/payments",
    summary="Create a new payment",
    description="Process a new payment transaction. Supports optional discount code application.",
    response_description="Created payment details",
    status_code=status.HTTP_201_CREATED
)
def create_payment(
    payment_create: PaymentCreate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Create a new payment record.
    
    Key Logic:
    1. Validates input data (amounts, transaction details).
    2. **Discount Logic:** Checks for `discount_code`. Validates existence, expiry, and limits. Calculates new total.
    3. **Hash Generation:** Creates secure hashes (`transaction_hash`, `payment_hash`) for data integrity.
    4. Persists the payment to the database.
    """
    try:
        # Validate critical fields
        if not payment_create.t_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction data (t_data) is required"
            )
        if payment_create.amount < 0 or (payment_create.t_data.amount is not None and payment_create.t_data.amount < 0):
             # Note: t_data.amount is optional in model but logic implies it exists or we trust the outer amount
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        
        # Get current timestamp
        now = datetime.now()
        timestamp = int(now.timestamp())
        
        # Generate hashes
        # These hashes are used to ensure the transaction record hasn't been tampered with
        try:
            transaction_hash = generate_transaction_validation_hash()
            payment_hash = generate_payment_hash()
        except Exception as e:
            logger.error(f"Failed to generate hashes: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate payment identifiers"
            )
        
        # Handle discount application
        original_amount = payment_create.amount
        final_amount = payment_create.amount
        discount_applied = None
        discount_amount = 0.0
        
        # If a discount code is provided, we attempt to validate and apply it
        if payment_create.discount_code:
            try:
                discount = get_discount_by_code(payment_create.discount_code)
                if not discount:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Discount code '{payment_create.discount_code}' not found"
                    )
                
                # Validate discount code status
                if not discount.get("active", True):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Discount code is not active"
                    )
                
                # Check expiration date
                if discount.get("expires_at"):
                    try:
                        expires_at = datetime.fromisoformat(discount["expires_at"])
                        if now > expires_at:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Discount code has expired"
                            )
                    except ValueError:
                        # If date parsing fails, ignore expiration check (fail open safe? or fail closed?)
                        # Current logic: ignore check if date is bad.
                        pass
                
                # Check usage limits
                max_uses = discount.get("max_uses")
                current_uses = discount.get("current_uses", 0)
                if max_uses is not None and current_uses >= max_uses:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Discount code has reached its usage limit"
                    )
                
                # Calculate discount amount
                discount_type = discount["discount_type"]
                discount_value = discount["discount_value"]
                
                if discount_type == "percentage":
                    discount_amount = original_amount * (discount_value / 100)
                elif discount_type == "fixed":
                    discount_amount = min(discount_value, original_amount)  # Don't exceed original amount
                
                final_amount = max(0, original_amount - discount_amount)
                discount_applied = payment_create.discount_code
                
                # Update discount usage count in DB
                updated_discount = discount.copy()
                updated_discount["current_uses"] = current_uses + 1
                update_existing_discount_in_db(payment_create.discount_code, updated_discount)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error applying discount: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to apply discount code"
                )

        # Build the payment object
        # Note: We convert session_id and parking_lot_id to strings for consistency with legacy JSON format
        payment = {
            "transaction": transaction_hash,
            "amount": final_amount,
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
            "parking_lot_id": str(payment_create.parking_lot_id),
            "original_amount": original_amount if discount_applied else None,
            "discount_applied": discount_applied,
            "discount_amount": discount_amount if discount_applied else None
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
    description="Update payment details. Only available to ADMIN users.",
    response_description="Updated payment details",
    status_code=status.HTTP_200_OK
)
def update_payment(
    payment_id: str,
    payment_update: PaymentUpdate,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Update a payment record.
    
    Logic:
    1. Enforces ADMIN role.
    2. Loads existing payment.
    3. Merges new data (partial update).
    4. Persists changes.
    """
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
