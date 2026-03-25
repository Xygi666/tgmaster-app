from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.audience import (
    AudienceSourceType,
    LastSeenBucket,
    ParseJobStatus,
)


# ---------- SOURCES ----------

class AudienceSourceBase(BaseModel):
    type: AudienceSourceType
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class AudienceSourceCreate(AudienceSourceBase):
    # пока достаточно username; external_id заполнится при первом успешном парсинге
    pass


class AudienceSourceRead(AudienceSourceBase):
    id: int
    external_id: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # orm_mode в Pydantic v2


# ---------- PARSE JOBS ----------

class ParseJobCreate(BaseModel):
    source_id: int
    mode: str = "members_full"
    limit_members: Optional[int] = None  # 0/None = без лимита


class ParseJobRead(BaseModel):
    id: int
    source_id: int
    mode: str
    status: ParseJobStatus
    total_items: Optional[int]
    processed_items: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class ParseJobProgress(BaseModel):
    id: int
    status: ParseJobStatus
    processed_items: int
    total_items: Optional[int]

    class Config:
        from_attributes = True


# ---------- MEMBERS & FILTERS ----------

class AudienceMemberRead(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    lang_code: Optional[str]
    is_bot: bool
    last_seen_bucket: LastSeenBucket
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


class AudienceMembersFilter(BaseModel):
    source_ids: Optional[List[int]] = None
    has_username: Optional[bool] = None
    is_bot: Optional[bool] = None
    activity: Optional[List[LastSeenBucket]] = None

    # пагинация
    offset: int = 0
    limit: int = 50
