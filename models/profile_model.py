from pydantic import BaseModel
from typing import Optional


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None