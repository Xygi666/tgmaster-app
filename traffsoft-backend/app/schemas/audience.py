from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.audience import (
    AudienceSourceType,
    LastSeenBucket,
    ParseJobStatus,
    ParseMode,
)


class AudienceSourceCreate(BaseModel):
    type: AudienceSourceType
    link: str = Field(..., description="Ссылка, username (@channel) или invite-ссылка")
    title: Optional[str] = None
    description: Optional[str] = None


class AudienceSourceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class AudienceSourceRead(BaseModel):
    id: int
    type: str
    external_id: Optional[str] = None
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    member_count: Optional[int] = None
    is_verified: bool
    is_private: bool
    last_parsed_at: Optional[datetime] = None
    parse_errors: int
    created_at: datetime

    class Config:
        from_attributes = True


class SourceStats(BaseModel):
    source_id: int
    total_members: int
    new_members_today: int
    active_last_day: int
    active_last_week: int
    active_last_month: int
    long_ago: int
    hidden: int
    bots: int
    with_usernames: int
    with_phones: int
    with_bio: int
    with_photos: int
    languages: dict[str, int]
    countries: dict[str, int]


class ParseJobCreate(BaseModel):
    source_id: int
    mode: ParseMode = ParseMode.members_full
    limit_members: Optional[int] = Field(None, description="Лимит участников (None = без лимита)")
    delay_ms: int = Field(500, ge=100, le=10000, description="Задержка между запросами, мс")
    skip_bots: bool = True
    skip_deleted: bool = True


class ParseJobRead(BaseModel):
    id: int
    source_id: int
    mode: str
    status: str
    limit_members: Optional[int] = None
    delay_ms: int
    skip_bots: bool
    skip_deleted: bool
    total_items: Optional[int] = None
    processed_items: int
    new_members: int
    skipped_members: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ParseJobProgress(BaseModel):
    id: int
    status: str
    processed_items: int
    new_members: int
    skipped_members: int
    total_items: Optional[int] = None
    error_message: Optional[str] = None


class ParseJobList(BaseModel):
    id: int
    source_id: int
    source_title: Optional[str] = None
    mode: str
    status: str
    processed_items: int
    new_members: int
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberFilters(BaseModel):
    source_ids: Optional[list[int]] = None
    segment_id: Optional[int] = None
    has_username: Optional[bool] = Field(None, description="Есть username (@)")
    has_phone: Optional[bool] = Field(None, description="Есть номер телефона")
    has_bio: Optional[bool] = Field(None, description="Есть био/описание")
    is_bot: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_deleted: Optional[bool] = None
    activity: Optional[list[str]] = Field(None, description=f"Фильтр по активности: {[b.value for b in LastSeenBucket]}")
    lang_codes: Optional[list[str]] = Field(None, description="Коды языков: ru, en, uk, de...")
    countries: Optional[list[str]] = Field(None, description="Коды стран: RU, UA, US, DE...")
    sources_count_min: Optional[int] = Field(None, ge=1)
    sources_count_max: Optional[int] = None
    search: Optional[str] = Field(None, description="Поиск по username, имени, bio")
    offset: int = 0
    limit: int = 50


class AudienceMemberRead(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    lang_code: Optional[str] = None
    country_code: Optional[str] = None
    is_bot: bool
    is_verified: bool
    is_scam: bool
    is_fake: bool
    is_deleted: bool
    has_photo: bool
    has_phone: bool
    last_seen_bucket: str
    last_seen_at: Optional[datetime] = None
    account_created_at: Optional[datetime] = None
    sources_count: int
    sources: Optional[list[str]] = Field(None, description="Source titles где состоит")
    created_at: datetime

    class Config:
        from_attributes = True


class MemberExportRequest(BaseModel):
    filters: MemberFilters
    format: str = Field("csv", description="csv, txt, json, phones")
    include_columns: Optional[list[str]] = Field(
        None,
        description="username, first_name, last_name, phone, lang_code, bio, last_seen, sources_count"
    )


class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    filters: Optional[dict] = None
    source_ids: Optional[list[int]] = None


class SegmentRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    filters: Optional[dict] = None
    source_ids: Optional[list[int]] = None
    member_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExclusionCreate(BaseModel):
    member_id: int
    reason: str


class ExclusionByUsername(BaseModel):
    usernames: list[str] = Field(..., min_length=1, max_length=1000)
    reason: str = "manual_exclusion"


class AnalyticsOverview(BaseModel):
    total_sources: int
    total_members: int
    members_with_usernames: int
    members_with_phones: int
    members_with_bio: int
    active_last_week: int
    active_last_month: int
    bots_count: int
    unique_languages: int
    top_sources: list[dict]
    top_languages: list[dict[str, int]]


class SourceOverlap(BaseModel):
    source_a_id: int
    source_b_id: int
    source_a_title: Optional[str] = None
    source_b_title: Optional[str] = None
    intersection_count: int
    intersection_percent_a: float
    intersection_percent_b: float


class ActivityStats(BaseModel):
    date: str
    new_members: int
    active_members: int
