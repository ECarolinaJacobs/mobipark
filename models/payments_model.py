from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException, status
from typing import Optional


class TData(BaseModel):
    """Nested transaction data"""

    amount: Optional[float] = Field(None, ge=0, description="Transaction amount")
    date: Optional[str] = Field(None, description="Transaction date string")
    method: Optional[str] = Field(None, description="Payment method (e.g., 'ideal', 'creditcard')")
    issuer: Optional[str] = Field(None, description="Card or bank issuer")
    bank: Optional[str] = Field(None, description="Bank name")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative",
            )
        return v


class Payment(BaseModel):
    """Complete payment model matching your JSON structure"""

    transaction: str = Field(..., description="Unique transaction ID")
    amount: float = Field(ge=0, description="Total payment amount")
    initiator: str = Field(..., description="User who initiated the payment")
    created_at: str = Field(..., description="Creation timestamp")
    completed: str = Field(..., description="Completion timestamp")
    hash: str = Field(..., description="Payment validation hash")
    t_data: TData = Field(..., description="Nested transaction details")
    session_id: str = Field(..., description="Associated parking session ID")
    parking_lot_id: str = Field(..., description="Associated parking lot ID")
    original_amount: Optional[float] = Field(None, ge=0, description="Original amount before discount")
    discount_applied: Optional[str] = Field(None, description="Discount code applied")
    discount_amount: Optional[float] = Field(None, ge=0, description="Amount discounted")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative",
            )
        return v


class PaymentCreate(BaseModel):
    """Model for creating a payment - only fields the user provides"""

    amount: float = Field(ge=0, description="Payment amount")
    session_id: int = Field(..., description="Parking session ID")
    parking_lot_id: int = Field(..., description="Parking lot ID")
    t_data: TData = Field(..., description="Transaction details")
    completed: Optional[str] = Field(None, description="Optional completion timestamp")
    discount_code: Optional[str] = Field(None, description="Optional discount code to apply")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative",
            )
        return v


class PaymentUpdate(BaseModel):
    transaction: Optional[str] = Field(None, description="Transaction ID (immutable)")
    amount: Optional[float] = Field(None, ge=0, description="New amount")
    completed: Optional[str] = Field(None, description="New completion timestamp")
    t_data: Optional[TData] = Field(None, description="Updated transaction details")
    session_id: Optional[int] = Field(None, description="New session ID")
    parking_lot_id: Optional[int] = Field(None, description="New parking lot ID")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative",
            )
        return v
