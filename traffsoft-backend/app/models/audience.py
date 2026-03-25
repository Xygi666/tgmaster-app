from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AudienceSourceType(str, Enum):
    telegram_group = "telegram_group"
    telegram_channel = "telegram_channel"


class ParseJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class LastSeenBucket(str, Enum):
    online = "online"
    day = "day"
    week = "week"
    month = "month"
    long_ago = "long_ago"
    unknown = "unknown"


class AudienceSource(Base):
    __tablename__ = "audience_sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    parse_jobs: Mapped[list["ParseJob"]] = relationship("ParseJob", back_populates="source", cascade="all, delete-orphan")
    source_members: Mapped[list["SourceMember"]] = relationship("SourceMember", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("type", "external_id", name="uq_source_type_external_id"),
    )


class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("audience_sources.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False, default="members_full")
    status: Mapped[str] = mapped_column(String, nullable=False, default=ParseJobStatus.pending.value)
    total_items: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["AudienceSource"] = relationship("AudienceSource", back_populates="parse_jobs")


class AudienceMember(Base):
    __tablename__ = "audience_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    lang_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_bucket: Mapped[str] = mapped_column(String, nullable=False, default=LastSeenBucket.unknown.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources: Mapped[list["SourceMember"]] = relationship("SourceMember", back_populates="member", cascade="all, delete-orphan")


class SourceMember(Base):
    __tablename__ = "source_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("audience_sources.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("audience_members.id", ondelete="CASCADE"), nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    source: Mapped["AudienceSource"] = relationship("AudienceSource", back_populates="source_members")
    member: Mapped["AudienceMember"] = relationship("AudienceMember", back_populates="sources")

    __table_args__ = (
        UniqueConstraint("source_id", "member_id", name="uq_source_member"),
    )
