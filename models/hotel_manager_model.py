from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class HotelManagerCreate(BaseModel):
    """model for admin to create a hotel manager account"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique username for the hotel manager",
        examples=["john_hotel_mgr"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Full name of the hotel manager",
        examples=["John Smith"],
    )
    password: str = Field(
        ..., min_length=6, description="Password (minimum 6 characters)", examples=["secure123"]
    )
    parking_lot_id: str = Field(
        ..., description="Id of the parking lot this hotel manager will manage", examples=["101"]
    )
    email: Optional[str] = Field(None, description="Contact email address", examples=["john@hotel.com"])
    phone: Optional[str] = Field(None, description="Contact phone number", examples=["+1234567890"])

    @field_validator("parking_lot_id")
    @classmethod
    def validate_parking_lot_id(cls, v):
        if not v.isdigit():
            raise ValueError("Parking lot Id must be numeric")
        return v


class HotelDiscountCodeCreate(BaseModel):
    """model for hotel managers to create 100% discount codes for their guests"""

    code: str = Field(..., min_length=1, max_length=50, description="Discount code", examples=["SUMMER2025"])
    check_in_date: str = Field(
        ..., description="Guest check-in date (ISO format YYYY-MM-DD)", examples=["2025-07-15"]
    )
    check_out_date: str = Field(
        ..., description="Guest check-out date (ISO format YYYY-MM-DD)", examples=["2025-07-20"]
    )
    guest_name: Optional[str] = Field(
        None, max_length=100, description="Name of the guest (optional)", examples=["Jane Doe"]
    )
    notes: Optional[str] = Field(
        None, max_length=500, description="Additional notes about this code", examples=["VIP guest"]
    )

    @field_validator("check_in_date", "check_out_date")
    @classmethod
    def validate_dates(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Use ISO format (YYYY-MM-DD)")
        return v

    @field_validator("check_out_date")
    @classmethod
    def validate_checkout_after_checkin(cls, v, info):
        if "check_in_date" in info.data:
            check_in = datetime.fromisoformat(info.data["check_in_date"])
            check_out = datetime.fromisoformat(v)
            if check_out <= check_in:
                raise ValueError("Check-out date must be after check-in date")
            return v


class HotelDiscountCode(BaseModel):
    """complete hotel discount code model"""

    code: str = Field(..., description="The discount code", examples=["SUMMER2025"])
    discount_type: str = Field(default="percentage", description="Type of discount (always percentage)")
    discount_value: float = Field(default=100.0, description="Discount value (always 100%)")
    max_uses: int = Field(default=1, description="Maximum number of times code can be used")
    current_uses: int = Field(default=0, description="Number of times this code has been used")
    active: bool = Field(default=True, description="Whether discount code is currently active")
    created_at: str = Field(
        ..., description="Timestamp when the code was created", examples=["15-07-2025 10:30:451721041845"]
    )
    check_in_date: str = Field(..., description="Guest check-in date", examples=["2025-07-15"])
    check_out_date: str = Field(..., description="Guest check-out date", examples=["2025-07-20"])
    parking_lot_id: str = Field(
        ..., description="Id of the parking lot for this discount code", examples=["101"]
    )
    created_by: str = Field(
        ..., description="Username of the hotel manager who created this code", examples=["john_hotel_mgr"]
    )
    guest_name: Optional[str] = Field(None, description="Name of the guest", examples=["Jane Doe"])
    notes: Optional[str] = Field(None, description="Additional notes", examples=["VIP guest"])
    is_hotel_code: bool = Field(
        default=True, description="Flag to distinguish hotel codes from admin discount codes"
    )
