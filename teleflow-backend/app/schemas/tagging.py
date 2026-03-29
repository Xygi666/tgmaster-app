from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.tagging import TaggingMode, TaggingSource, TaggingStatus


class TaggingJobCreate(BaseModel):
    name: Optional[str] = None
    account_id: Optional[int] = None
    target_link: str = Field(..., description="Ссылка на чат/группу/канал")
    template: Optional[str] = Field(None, description="Текст с @username. Пример: Привет, @{username}!")
    source_type: TaggingSource = TaggingSource.sources
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: TaggingMode = TaggingMode.balanced
    delay_min_ms: int = Field(10000, ge=2000, le=120000)
    delay_max_ms: int = Field(30000, ge=2000, le=300000)
    limit_users: Optional[int] = Field(None, ge=1, le=100000)
    batch_size: int = Field(5, ge=1, le=20)
    skip_no_username: bool = True
    lang_codes: Optional[list[str]] = None


class TaggingJobUpdate(BaseModel):
    name: Optional[str] = None
    delay_min_ms: Optional[int] = None
    delay_max_ms: Optional[int] = None
    limit_users: Optional[int] = None


class TaggingJobRead(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    target_link: Optional[str] = None
    target_title: Optional[str] = None
    message_id: Optional[int] = None
    message_text: Optional[str] = None
    template: Optional[str] = None
    source_type: str
    source_ids: Optional[list[int]] = None
    custom_usernames: Optional[list[str]] = None
    mode: str
    status: str
    delay_min_ms: int
    delay_max_ms: int
    limit_users: Optional[int] = None
    batch_size: int
    skip_no_username: bool
    lang_codes: Optional[list[str]] = None
    total_users: int
    processed_users: int
    tagged_users: int
    skipped: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaggingJobList(BaseModel):
    id: int
    name: Optional[str] = None
    account_id: Optional[int] = None
    account_phone: Optional[str] = None
    target_title: Optional[str] = None
    template: Optional[str] = None
    source_type: str
    mode: str
    status: str
    total_users: int
    processed_users: int
    tagged_users: int
    errors_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaggingProgress(BaseModel):
    id: int
    status: str
    processed_users: int
    total_users: int
    tagged_users: int
    skipped: int
    errors_count: int
    error_message: Optional[str] = None


class TaggingLogRead(BaseModel):
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


class TaggingStats(BaseModel):
    total_jobs: int
    running_jobs: int
    completed_today: int
    total_tagged: int
    total_errors: int
