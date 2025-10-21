from pydantic import BaseModel, Field
from typing import Optional


class TData(BaseModel):
    """Nested transaction data"""
    amount: float
    date: str  # Format: "2025-07-14 22:30:17"
    method: str
    issuer: str
    bank: str


class Payment(BaseModel):
    """Complete payment model matching your JSON structure"""
    transaction: str
    amount: float
    initiator: str
    created_at: str  # Format: "14-07-2025 22:30:171752525017"
    completed: str  # Format: "14-07-2025 22:30:171752525024"
    hash: str
    t_data: TData
    session_id: str  # Stored as string in JSON
    parking_lot_id: str  # Stored as string in JSON


class PaymentCreate(BaseModel):
    """Model for creating a payment - only fields the user provides"""
    amount: float
    session_id: int  # User sends as int, we convert to string
    parking_lot_id: int  # User sends as int, we convert to string
    t_data: TData
    completed: Optional[str] = None


class PaymentUpdate(BaseModel):
    transaction: Optional[float] = None
    amount: Optional[float] = None
    completed: Optional[str] = None
    t_data: Optional[TData] = None
    session_id: Optional[int] = None
    parking_lot_id: Optional[int] = None