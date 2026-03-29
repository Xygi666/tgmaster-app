from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
