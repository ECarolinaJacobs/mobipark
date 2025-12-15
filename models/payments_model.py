from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException, status
from typing import Optional


class TData(BaseModel):
    """Nested transaction data"""
    amount: Optional[float] = Field(None, ge=0)
    date: Optional[str] = None
    method: Optional[str] = None
    issuer: Optional[str] = None
    bank: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        return v


class Payment(BaseModel):
    """Complete payment model matching your JSON structure"""
    transaction: str
    amount: float = Field(ge=0)
    initiator: str
    created_at: str  # Format: "14-07-2025 22:30:171752525017"
    completed: str  # Format: "14-07-2025 22:30:171752525024"
    hash: str
    t_data: TData
    session_id: str  # Stored as string in JSON
    parking_lot_id: str  # Stored as string in JSON
    original_amount: Optional[float] = Field(None, ge=0, description="Original amount before discount")
    discount_applied: Optional[str] = Field(None, description="Discount code applied")
    discount_amount: Optional[float] = Field(None, ge=0, description="Amount discounted")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        return v


class PaymentCreate(BaseModel):
    """Model for creating a payment - only fields the user provides"""
    amount: float = Field(ge=0)
    session_id: int  # User sends as int, we convert to string
    parking_lot_id: int  # User sends as int, we convert to string
    t_data: TData
    completed: Optional[str] = None
    discount_code: Optional[str] = Field(None, description="Optional discount code to apply")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        return v


class PaymentUpdate(BaseModel):
    transaction: Optional[str] = None
    amount: Optional[float] = Field(None, ge=0)
    completed: Optional[str] = None
    t_data: Optional[TData] = None
    session_id: Optional[int] = None
    parking_lot_id: Optional[int] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Transaction/Tdata (amount) cannot be negative"
            )
        return v