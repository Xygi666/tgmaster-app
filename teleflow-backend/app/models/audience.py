from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AudienceSourceType(str, Enum):
    telegram_group = "telegram_group"
    telegram_channel = "telegram_channel"
    telegram_user = "telegram_user"


class ParseJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ParseMode(str, Enum):
    members_full = "members_full"
    members_lite = "members_lite"
    members_active = "members_active"
    admins = "admins"
    messages = "messages"
    messages_media = "messages_media"


class LastSeenBucket(str, Enum):
    online = "online"
    day = "day"
    week = "week"
    month = "month"
    long_ago = "long_ago"
    hidden = "hidden"
    unknown = "unknown"


class AudienceSource(Base):
    __tablename__ = "audience_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parse_errors: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    parse_jobs: Mapped[list["ParseJob"]] = relationship("ParseJob", back_populates="source", cascade="all, delete-orphan")
    source_members: Mapped[list["SourceMember"]] = relationship("SourceMember", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("type", "external_id", name="uq_source_type_external_id"),
        UniqueConstraint("type", "username", name="uq_source_type_username"),
        Index("ix_source_username_lower", "username"),
    )


class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("audience_sources.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default=ParseMode.members_full.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ParseJobStatus.pending.value)
    limit_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delay_ms: Mapped[int] = mapped_column(Integer, default=500)
    skip_bots: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_deleted: Mapped[bool] = mapped_column(Boolean, default=True)
    total_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    new_members: Mapped[int] = mapped_column(Integer, default=0)
    skipped_members: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["AudienceSource"] = relationship("AudienceSource", back_populates="parse_jobs")

    __table_args__ = (
        Index("ix_job_status_created", "status", "created_at"),
    )


class AudienceMember(Base):
    __tablename__ = "audience_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    lang_code: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_scam: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fake: Mapped[bool] = mapped_column(Boolean, default=False)
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    has_photo: Mapped[bool] = mapped_column(Boolean, default=True)
    has_phone: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_bucket: Mapped[str] = mapped_column(String(16), nullable=False, default=LastSeenBucket.unknown.value)
    account_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources: Mapped[list["SourceMember"]] = relationship("SourceMember", back_populates="member", cascade="all, delete-orphan")
    exclusions: Mapped[list["MemberExclusion"]] = relationship("MemberExclusion", back_populates="member", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_member_lang_active", "lang_code", "last_seen_bucket"),
        Index("ix_member_phone", "phone"),
        Index("ix_member_username_lower", "username"),
    )


class SourceMember(Base):
    __tablename__ = "source_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("audience_sources.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("audience_members.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    previous_parse_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped["AudienceSource"] = relationship("AudienceSource", back_populates="source_members")
    member: Mapped["AudienceMember"] = relationship("AudienceMember", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("source_id", "member_id", name="uq_source_member"),
        UniqueConstraint("source_id", "member_id", "previous_parse_id", name="uq_source_member_parse"),
    )


class MemberExclusion(Base):
    __tablename__ = "member_exclusions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("audience_members.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    excluded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    member: Mapped["AudienceMember"] = relationship("AudienceMember", back_populates="exclusions")


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
