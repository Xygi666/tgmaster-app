from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.inviting import InvitingMode, InvitingSource, InvitingStatus


class InvitingJobCreate(BaseModel):
    name: Optional[str] = None
    account_id: Optional[int] = None
    target_link: str = Field(..., description="Ссылка на группу/канал куда приглашать")
    source_type: InvitingSource = InvitingSource.sources
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: InvitingMode = InvitingMode.balanced
    delay_min_ms: int = Field(30000, ge=5000, le=120000)
    delay_max_ms: int = Field(60000, ge=5000, le=300000)
    limit_users: Optional[int] = Field(None, ge=1, le=100000)
    skip_already_in: bool = True
    skip_bots: bool = True
    lang_codes: Optional[list[str]] = None
    activity_filter: Optional[list[str]] = None


class InvitingJobUpdate(BaseModel):
    name: Optional[str] = None
    delay_min_ms: Optional[int] = None
    delay_max_ms: Optional[int] = None
    limit_users: Optional[int] = None


class InvitingJobRead(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    target_link: Optional[str] = None
    target_title: Optional[str] = None
    source_type: str
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: str
    status: str
    delay_min_ms: int
    delay_max_ms: int
    limit_users: Optional[int] = None
    skip_already_in: bool
    skip_bots: bool
    lang_codes: Optional[list[str]] = None
    activity_filter: Optional[list[str]] = None
    total_users: int
    processed_users: int
    invited_users: int
    already_in: int
    skipped: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class InvitingJobList(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    account_phone: Optional[str] = None
    target_title: Optional[str] = None
    source_type: str
    mode: str
    status: str
    total_users: int
    processed_users: int
    invited_users: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class InvitingProgress(BaseModel):
    id: int
    status: str
    processed_users: int
    total_users: int
    invited_users: int
    already_in: int
    skipped: int
    errors_count: int
    error_message: Optional[str] = None


class InvitingLogRead(BaseModel):
    id: int
    job_id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    action: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class InvitingStats(BaseModel):
    total_jobs: int
    running_jobs: int
    completed_today: int
    total_invited: int
    total_errors: int
