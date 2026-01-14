from pydantic import BaseModel, Field, field_validator
from typing import Optional
from fastapi import HTTPException, status
from datetime import datetime


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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Parking lot Id must be a digit"
            )
        return v


class HotelDiscountCodeCreate(BaseModel):
    """model for hotel managers to create 100% discount codes for their guests"""

    code: str = Field(..., min_length=1, max_length=50, description="Discount code")
    check_in_date: str = Field(..., description="Guest check-in date (ISO format YYYY-MM-DD)")
    check_out_date: str = Field(..., description="Guest check-out date (ISO format YYYY-MM-DD)")
    guest_name: Optional[str] = Field(None, max_length=100, description="Name of the guest (optional)")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes about this code")

    @field_validator("check_in_date", "check_out_date")
    @classmethod
    def validate_dates(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid date format: {v}. Use ISO format (YYYY-MM-DD)",
            )
        return v

    @field_validator("check_out_date")
    @classmethod
    def validate_checkout_after_checkin(cls, v, info):
        if "check_in_date" in info.data:
            check_in = datetime.fromisoformat(info.data["check_in_date"])
            check_out = datetime.fromisoformat(v)
            if check_out <= check_in:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Check-out date must be after check-in date",
                )
            return v


class HotelDiscountCode(BaseModel):
    """complete hotel discount code model"""

    code: str
    discount_type: str = "percentage"
    discount_value: float = 100.0
    max_uses: int = 1  # single use codes
    current_uses: int = 0
    active: bool = True
    created_at: str
    check_in_date: str
    check_out_date: str
    parking_lot_id: str  # for which parking lot the code is valid for
    created_by: str  # hotel manager username
    guest_name: Optional[str] = None
    notes: Optional[str] = None
    is_hotel_code: bool = True  # flag to distinguish hotel from admin discount codes
