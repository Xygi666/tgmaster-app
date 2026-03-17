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


class AccountRead(AccountBase):
    id: int
    last_activity_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
