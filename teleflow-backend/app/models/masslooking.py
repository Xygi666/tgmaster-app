from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MasslookingMode(str, Enum):
    safe = "safe"
    balanced = "balanced"
    aggressive = "aggressive"


class MasslookingSource(str, Enum):
    dialogs = "dialogs"
    sources = "sources"
    custom = "custom"


class MasslookingStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class MasslookingJob(Base):
    __tablename__ = "masslooking_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default=MasslookingSource.dialogs.value)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_usernames: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default=MasslookingMode.balanced.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=MasslookingStatus.pending.value)
    delay_min_ms: Mapped[int] = mapped_column(Integer, default=3000)
    delay_max_ms: Mapped[int] = mapped_column(Integer, default=8000)
    limit_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skip_bots: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_no_stories: Mapped[bool] = mapped_column(Boolean, default=True)
    lang_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    activity_filter: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    processed_users: Mapped[int] = mapped_column(Integer, default=0)
    stories_watched: Mapped[int] = mapped_column(Integer, default=0)
    users_with_stories: Mapped[int] = mapped_column(Integer, default=0)
    users_skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship("Account", back_populates="masslooking_jobs")
    logs: Mapped[list["MasslookingLog"]] = relationship("MasslookingLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ml_job_status", "status", "created_at"),
    )


class MasslookingLog(Base):
    __tablename__ = "masslooking_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("masslooking_jobs.id", ondelete="CASCADE"), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    watched_stories: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["MasslookingJob"] = relationship("MasslookingJob", back_populates="logs")

    __table_args__ = (
        Index("ix_ml_log_job", "job_id", "timestamp"),
    )
