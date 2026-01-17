from typing import List, Dict, Optional
from datetime import datetime
import logging
import uuid

from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from utils.session_manager import get_session
from utils.storage_utils import (
    get_payment_data_by_id,
    save_new_refund_to_db,
    get_refund_by_id,
    load_refunds_data_from_db,
    update_existing_refund_in_db,
    get_refunds_by_transaction_id,
    get_discount_by_code,
    save_new_discount_to_db,
    load_discounts_data_from_db,
    update_existing_discount_in_db,
    get_refunds_for_user
)
from models.refunds_model import (
    RefundCreate, 
    Refund, 
    RefundUpdate, 
    DiscountCodeCreate, 
    DiscountCode
)
from utils.session_calculator import generate_payment_hash

# Set up logging
logger = logging.getLogger(__name__)

ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"


def require_auth(request: Request) -> Dict[str, str]:
    """
    Dependency to verify user authentication.
    
    Checks for the Authorization header and validates the session.
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


def require_admin(request: Request) -> Dict[str, str]:
    """
    Dependency to verify ADMIN privileges.
    
    Extends require_auth to check for the ADMIN role.
    """
    session_user = require_auth(request)
    
    if session_user["role"] != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return session_user


# Initialize router without default tags to allow granular tagging (refunds vs discounts)
router = APIRouter(
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Not Found - Resource does not exist"}
    }
)


# --- Refund Endpoints ---

@router.post(
    "/refunds",
    summary="Create a new refund",
    description="Process a refund for an existing transaction. Only ADMIN users can initiate refunds.",
    tags=["refunds"],
    response_description="Created refund details",
    status_code=status.HTTP_201_CREATED
)
def create_refund(
    refund_create: RefundCreate,
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    Create a refund record.
    
    Logic:
    1. Validates the original payment exists.
    2. checks if the requested refund amount is valid (cannot exceed remaining balance).
    3. Generates a new refund ID and hash for integrity.
    4. Persists the refund.
    """
    try:
        # Validate the original payment exists
        original_payment = get_payment_data_by_id(refund_create.original_transaction_id)
        if not original_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original payment with transaction ID {refund_create.original_transaction_id} not found"
            )
        
        # Check if refund amount is valid
        # We must ensure we don't refund more than the original payment amount
        original_amount = original_payment["amount"]
        
        # Get existing refunds for this transaction to calculate remaining balance
        existing_refunds = get_refunds_by_transaction_id(refund_create.original_transaction_id)
        total_refunded = sum(refund["amount"] for refund in existing_refunds if refund.get("status") == "completed")
        
        if refund_create.amount > (original_amount - total_refunded):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Refund amount ({refund_create.amount}) exceeds remaining refundable amount ({original_amount - total_refunded})"
            )
        
        # Generate refund details
        now = datetime.now()
        timestamp = int(now.timestamp())
        refund_id = str(uuid.uuid4())
        
        # We reuse payment hash generation for refunds to maintain consistent security standards
        refund_hash = generate_payment_hash()
        
        # Build the refund object
        refund = {
            "refund_id": refund_id,
            "original_transaction_id": refund_create.original_transaction_id,
            "amount": refund_create.amount,
            "reason": refund_create.reason,
            "processed_by": session_user["username"],
            "created_at": f"{now.strftime('%d-%m-%Y %H:%M:%S')}{timestamp}",
            "status": "completed",
            "refund_hash": refund_hash
        }
        
        # Save the refund
        try:
            save_new_refund_to_db(refund)
        except Exception as e:
            logger.error(f"Failed to save refund: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save refund"
            )
        
        logger.info(f"Refund created: {refund_id} for transaction {refund_create.original_transaction_id} by {session_user['username']}")
        
        return JSONResponse(
            content=refund,
            status_code=status.HTTP_201_CREATED
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_refund: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/refunds/{refund_id}",
    summary="Get a refund by ID",
    description="Retrieve details of a specific refund. Users can only see refunds for their own payments.",
    tags=["refunds"],
    response_description="Refund details object"
)
def get_refund_by_id_endpoint(
    refund_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Retrieve a specific refund.
    
    Logic:
    1. Loads refund by ID.
    2. Authorization: Checks if the user owns the original payment (or is ADMIN).
    """
    try:
        refund = get_refund_by_id(refund_id)
        if not refund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Refund with ID {refund_id} not found"
            )
        
        # Check authorization - users can only see refunds for their own payments
        if session_user["role"] != ROLE_ADMIN:
            original_payment = get_payment_data_by_id(refund["original_transaction_id"])
            if not original_payment or original_payment["initiator"] != session_user["username"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access refunds for payments that are not your own"
                )
        
        return JSONResponse(content=refund, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_refund_by_id: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/refunds",
    summary="Get all refunds",
    description="List all refunds. Admins see all; users see only their own.",
    tags=["refunds"],
    response_description="List of refund objects"
)
def get_all_refunds(
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    List all accessible refunds.
    
    Logic:
    1. If ADMIN: Load and return all refunds.
    2. If USER: Join refunds with payments to return only those belonging to the user.
    """
    try:
        # Admins see all refunds
        if session_user["role"] == ROLE_ADMIN:
            refunds = load_refunds_data_from_db() or []
            return JSONResponse(content=refunds, status_code=status.HTTP_200_OK)
        
        # Regular users see only refunds for their own payments using JOIN
        user_refunds = get_refunds_for_user(session_user["username"])
        return JSONResponse(content=user_refunds, status_code=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to load refunds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load refunds"
        )


@router.get(
    "/refunds/transaction/{transaction_id}",
    summary="Get refunds for a transaction",
    description="List all refunds associated with a specific payment transaction.",
    tags=["refunds"],
    response_description="List of refund objects"
)
def get_refunds_for_transaction(
    transaction_id: str,
    session_user: Dict[str, str] = Depends(require_auth)
) -> JSONResponse:
    """
    Get all refunds for a specific payment.
    
    Logic:
    1. Validate transaction existence.
    2. Authorization: Check ownership of the transaction.
    3. Return associated refunds.
    """
    try:
        # Check if the transaction exists and user has access
        original_payment = get_payment_data_by_id(transaction_id)
        if not original_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Authorization check
        is_owner = original_payment["initiator"] == session_user["username"]
        is_admin = session_user["role"] == ROLE_ADMIN
        
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access refunds for payments that are not your own"
            )
        
        refunds = get_refunds_by_transaction_id(transaction_id)
        return JSONResponse(content=refunds, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load refunds for transaction {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load refunds"
        )


# --- Discount Code Management Endpoints ---

@router.post(
    "/discount-codes",
    summary="Create a new discount code",
    description="Create a new promotional discount code. Only ADMIN users can create codes.",
    tags=["discounts"],
    response_description="Created discount code details",
    status_code=status.HTTP_201_CREATED
)
def create_discount_code(
    discount_create: DiscountCodeCreate,
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    Create a new discount code.
    
    Logic:
    1. Enforce ADMIN role.
    2. Check for duplicate codes.
    3. Create record with `active=True`.
    """
    try:
        # Check if discount code already exists
        existing_discount = get_discount_by_code(discount_create.code)
        if existing_discount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Discount code '{discount_create.code}' already exists"
            )
        
        # Generate discount code details
        now = datetime.now()
        timestamp = int(now.timestamp())
        
        # Build the discount code object
        discount_code = {
            "code": discount_create.code,
            "discount_type": discount_create.discount_type,
            "discount_value": discount_create.discount_value,
            "max_uses": discount_create.max_uses,
            "current_uses": 0,
            "active": True,
            "created_at": f"{now.strftime('%d-%m-%Y %H:%M:%S')}{timestamp}",
            "expires_at": discount_create.expires_at
        }
        
        # Save the discount code
        try:
            save_new_discount_to_db(discount_code)
        except Exception as e:
            logger.error(f"Failed to save discount code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save discount code"
            )
        
        logger.info(f"Discount code created: {discount_create.code} by {session_user['username']}")
        
        return JSONResponse(
            content=discount_code,
            status_code=status.HTTP_201_CREATED
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_discount_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/discount-codes",
    summary="Get all discount codes",
    description="List all discount codes. Only ADMIN users can view all codes.",
    tags=["discounts"],
    response_description="List of discount code objects"
)
def get_all_discount_codes(
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    List all discount codes.
    
    Logic:
    1. Enforce ADMIN role.
    2. Return all records.
    """
    try:
        discount_codes = load_discounts_data_from_db() or []
        return JSONResponse(content=discount_codes, status_code=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to load discount codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load discount codes"
        )


@router.get(
    "/discount-codes/{code}",
    summary="Get a discount code by code",
    description="Retrieve details of a specific discount code. Only ADMIN users can view details.",
    tags=["discounts"],
    response_description="Discount code details"
)
def get_discount_code_by_code(
    code: str,
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    Retrieve a specific discount code.
    """
    try:
        discount_code = get_discount_by_code(code)
        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount code '{code}' not found"
            )
        
        return JSONResponse(content=discount_code, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_discount_code_by_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.put(
    "/discount-codes/{code}",
    summary="Update a discount code",
    description="Update an existing discount code (value, type, limits). Only ADMIN users can update codes.",
    tags=["discounts"],
    response_description="Updated discount code details"
)
def update_discount_code(
    code: str,
    discount_update: DiscountCodeCreate,
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    Update discount code details.
    
    Logic:
    1. Checks if code exists.
    2. Overwrites fields with new values (excludes usage counts).
    """
    try:
        # Check if discount code exists
        existing_discount = get_discount_by_code(code)
        if not existing_discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount code '{code}' not found"
            )
        
        # Update the discount code
        updated_discount = existing_discount.copy()
        updated_discount.update({
            "discount_type": discount_update.discount_type,
            "discount_value": discount_update.discount_value,
            "max_uses": discount_update.max_uses,
            "expires_at": discount_update.expires_at
        })
        
        # Save the updated discount code
        try:
            update_existing_discount_in_db(code, updated_discount)
        except Exception as e:
            logger.error(f"Failed to update discount code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update discount code"
            )
        
        logger.info(f"Discount code updated: {code} by {session_user['username']}")
        
        return JSONResponse(content=updated_discount, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_discount_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete(
    "/discount-codes/{code}",
    summary="Deactivate a discount code",
    description="Soft-delete a discount code (set active=False). Only ADMIN users can deactivate codes.",
    tags=["discounts"],
    response_description="Deactivated discount code details"
)
def deactivate_discount_code(
    code: str,
    session_user: Dict[str, str] = Depends(require_admin)
) -> JSONResponse:
    """
    Deactivate a discount code so it can no longer be used.
    """
    try:
        # Check if discount code exists
        existing_discount = get_discount_by_code(code)
        if not existing_discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount code '{code}' not found"
            )
        
        # Deactivate the discount code
        updated_discount = existing_discount.copy()
        updated_discount["active"] = False
        
        # Save the updated discount code
        try:
            update_existing_discount_in_db(code, updated_discount)
        except Exception as e:
            logger.error(f"Failed to deactivate discount code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate discount code"
            )
        
        logger.info(f"Discount code deactivated: {code} by {session_user['username']}")
        
        return JSONResponse(content=updated_discount, status_code=status.HTTP_200_OK)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in deactivate_discount_code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )