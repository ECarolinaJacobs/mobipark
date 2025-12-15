from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime


class RefundCreate(BaseModel):
    """Model for creating a refund"""
    original_transaction_id: str = Field(..., description="Transaction ID of the original payment to refund")
    amount: float = Field(..., ge=0, description="Amount to refund (must be positive and <= original payment amount)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for the refund")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Refund amount must be positive"
            )
        return v


class Refund(BaseModel):
    """Complete refund model"""
    refund_id: str = Field(..., description="Unique refund identifier")
    original_transaction_id: str = Field(..., description="Transaction ID of the original payment")
    amount: float = Field(..., ge=0, description="Refunded amount")
    reason: str = Field(..., description="Reason for the refund")
    processed_by: str = Field(..., description="Username of admin who processed the refund")
    created_at: str = Field(..., description="Timestamp when refund was created")
    status: str = Field(default="completed", description="Refund status")
    refund_hash: str = Field(..., description="Unique hash for the refund transaction")


class RefundUpdate(BaseModel):
    """Model for updating a refund (admin only)"""
    status: Optional[str] = Field(None, description="Update refund status")
    reason: Optional[str] = Field(None, min_length=1, max_length=500, description="Update refund reason")


class DiscountCode(BaseModel):
    """Model for discount codes"""
    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    discount_type: str = Field(..., description="Type of discount: 'percentage' or 'fixed'")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage or fixed amount)")
    max_uses: Optional[int] = Field(None, ge=1, description="Maximum number of uses (None for unlimited)")
    current_uses: int = Field(default=0, ge=0, description="Current number of uses")
    active: bool = Field(default=True, description="Whether the discount code is active")
    created_at: str = Field(..., description="When the discount code was created")
    expires_at: Optional[str] = Field(None, description="When the discount code expires")
    
    @field_validator('discount_type')
    @classmethod
    def validate_discount_type(cls, v):
        if v not in ['percentage', 'fixed']:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Discount type must be 'percentage' or 'fixed'"
            )
        return v
    
    @field_validator('discount_value')
    @classmethod
    def validate_discount_value(cls, v, info):
        if 'discount_type' in info.data and info.data['discount_type'] == 'percentage':
            if v > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Percentage discount cannot exceed 100%"
                )
        return v


class DiscountCodeCreate(BaseModel):
    """Model for creating discount codes"""
    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    discount_type: str = Field(..., description="Type of discount: 'percentage' or 'fixed'")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage or fixed amount)")
    max_uses: Optional[int] = Field(None, ge=1, description="Maximum number of uses (None for unlimited)")
    expires_at: Optional[str] = Field(None, description="When the discount code expires (ISO format)")
    
    @field_validator('discount_type')
    @classmethod
    def validate_discount_type(cls, v):
        if v not in ['percentage', 'fixed']:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Discount type must be 'percentage' or 'fixed'"
            )
        return v
    
    @field_validator('discount_value')
    @classmethod
    def validate_discount_value(cls, v, info):
        if 'discount_type' in info.data and info.data['discount_type'] == 'percentage':
            if v > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Percentage discount cannot exceed 100%"
                )
        return v


class ApplyDiscount(BaseModel):
    """Model for applying a discount to a payment"""
    discount_code: str = Field(..., min_length=1, max_length=50, description="Discount code to apply")