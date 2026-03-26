from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AccountBase(BaseModel):
    phone: str
    display_name: str
    status: str = "active"
    proxy: Optional[str] = None
    group_name: Optional[str] = None
    tasks_per_day: int = 0
    tasks_limit: int = 500


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    proxy: Optional[str] = None
    group_name: Optional[str] = None
    tasks_per_day: Optional[int] = None
    tasks_limit: Optional[int] = None


class AccountRead(AccountBase):
    id: int
    last_activity_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
