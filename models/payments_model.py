from pydantic import BaseModel
from datetime import datetime
from typing import Optional

    
class PaymentUpdate(BaseModel):
    amount: float
    t_data_method: Optional[str] = None
    t_data_issuer: Optional[str] = None
    t_data_bank: Optional[str] = None
    
class PaymentCreate(BaseModel):
    amount: float
    session_id: int
    parking_lot_id: int
    # Optional fields
    completed: Optional[str] = None
    t_data_method: Optional[str] = None
    t_data_issuer: Optional[str] = None
    t_data_bank: Optional[str] = None
    t_data_date: Optional[str] = None
    
