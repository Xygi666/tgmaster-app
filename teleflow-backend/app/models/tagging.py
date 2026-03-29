from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaggingMode(str, Enum):
    safe = "safe"
    balanced = "balanced"
    aggressive = "aggressive"


class TaggingSource(str, Enum):
    sources = "sources"
    custom = "custom"


class TaggingStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaggingJob(Base):
    __tablename__ = "tagging_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    target_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    template: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default=TaggingSource.sources.value)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_usernames: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default=TaggingMode.balanced.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TaggingStatus.pending.value)
    delay_min_ms: Mapped[int] = mapped_column(Integer, default=10000)
    delay_max_ms: Mapped[int] = mapped_column(Integer, default=30000)
    limit_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_size: Mapped[int] = mapped_column(Integer, default=5)
    skip_no_username: Mapped[bool] = mapped_column(Boolean, default=True)
    lang_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    processed_users: Mapped[int] = mapped_column(Integer, default=0)
    tagged_users: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship("Account", back_populates="tagging_jobs")
    logs: Mapped[list["TaggingLog"]] = relationship("TaggingLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tag_job_status", "status", "created_at"),
    )


class TaggingLog(Base):
    __tablename__ = "tagging_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("tagging_jobs.id", ondelete="CASCADE"), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["TaggingJob"] = relationship("TaggingJob", back_populates="logs")

    __table_args__ = (
        Index("ix_tag_log_job", "job_id", "timestamp"),
    )
