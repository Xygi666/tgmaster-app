from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.masslooking import MasslookingMode, MasslookingSource, MasslookingStatus


class MasslookingJobCreate(BaseModel):
    name: Optional[str] = None
    account_id: Optional[int] = None
    source_type: MasslookingSource = MasslookingSource.dialogs
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: MasslookingMode = MasslookingMode.balanced
    delay_min_ms: int = Field(3000, ge=1000, le=30000)
    delay_max_ms: int = Field(8000, ge=1000, le=60000)
    limit_users: Optional[int] = Field(None, ge=1, le=100000)
    skip_bots: bool = True
    skip_no_stories: bool = True
    lang_codes: Optional[list[str]] = None
    activity_filter: Optional[list[str]] = None


class MasslookingJobUpdate(BaseModel):
    name: Optional[str] = None
    delay_min_ms: Optional[int] = None
    delay_max_ms: Optional[int] = None
    limit_users: Optional[int] = None


class MasslookingJobRead(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    source_type: str
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: str
    status: str
    delay_min_ms: int
    delay_max_ms: int
    limit_users: Optional[int] = None
    skip_bots: bool
    skip_no_stories: bool
    lang_codes: Optional[list[str]] = None
    activity_filter: Optional[list[str]] = None
    total_users: int
    processed_users: int
    stories_watched: int
    users_with_stories: int
    users_skipped: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class MasslookingJobList(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    account_phone: Optional[str] = None
    source_type: str
    mode: str
    status: str
    total_users: int
    processed_users: int
    stories_watched: int
    users_with_stories: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class MasslookingProgress(BaseModel):
    id: int
    status: str
    processed_users: int
    total_users: int
    stories_watched: int
    users_with_stories: int
    users_skipped: int
    errors_count: int
    error_message: Optional[str] = None


class MasslookingLogRead(BaseModel):
    id: int
    job_id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    action: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    watched_stories: int
    timestamp: datetime

    class Config:
        from_attributes = True


class MasslookingStats(BaseModel):
    total_jobs: int
    running_jobs: int
    completed_today: int
    total_stories_watched: int
    total_users_processed: int
    total_errors: int
