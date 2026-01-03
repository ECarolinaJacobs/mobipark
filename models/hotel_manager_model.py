from pydantic import BaseModel, Field, field_validator
from typing import Optional
from fastapi import HTTPException, status


class HotelManagerCreate(BaseModel):
    """model for admin to create a hotel manager account"""

    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    parking_lot_id: str = Field(..., description="Id of the parking lot this hotel manager will manage")
    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("parking_lot_id")
    @classmethod
    def validate_parking_lot_id(cls, v):
        if not v.isdigit():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Parking lot Id must be a digit"
            )
        return v


class HotelDiscountCodeCreate(BaseModel):
    """model for hotel managers to create 100% discount codes for their guests"""

    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    max_uses: Optional[int] = Field(None, ge=1, description="Maximum number of uses (none for unlimited)")
    expires_at: Optional[str] = Field(None, description="When the discount code expires (ISO format)")
    guest_name: Optional[str] = Field(None, max_length=100, description="Name of the guest (optional)")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes about this code")


class HotelDiscountCode(BaseModel):
    """complete hotel discount code model"""

    code: str
    discount_type: str = "percentage"
    discount_value: float = 100.0
    max_uses: Optional[int] = None
    current_uses: int = 0
    active: bool = True
    created_at: str
    expires_at: Optional[str] = None
    parking_lot_id: str  # for which parking lot the code is valid for
    created_by: str  # hotel manager username
    guest_name: Optional[str] = None
    notes: Optional[str] = None
    is_hotel_code: bool = True  # flag to distinguis hotel from admin discount codes
