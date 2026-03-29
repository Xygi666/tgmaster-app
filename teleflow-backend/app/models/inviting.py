from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, Text, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvitingMode(str, Enum):
    safe = "safe"
    balanced = "balanced"
    aggressive = "aggressive"


class InvitingSource(str, Enum):
    sources = "sources"
    custom = "custom"


class InvitingStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class InvitingJob(Base):
    __tablename__ = "inviting_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    target_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default=InvitingSource.sources.value)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    custom_usernames: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default=InvitingMode.balanced.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=InvitingStatus.pending.value)
    delay_min_ms: Mapped[int] = mapped_column(Integer, default=30000)
    delay_max_ms: Mapped[int] = mapped_column(Integer, default=60000)
    limit_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skip_already_in: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_bots: Mapped[bool] = mapped_column(Boolean, default=True)
    lang_codes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    activity_filter: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    processed_users: Mapped[int] = mapped_column(Integer, default=0)
    invited_users: Mapped[int] = mapped_column(Integer, default=0)
    already_in: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship("Account", back_populates="inviting_jobs")
    logs: Mapped[list["InvitingLog"]] = relationship("InvitingLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_inv_job_status", "status", "created_at"),
    )


class InvitingLog(Base):
    __tablename__ = "inviting_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("inviting_jobs.id", ondelete="CASCADE"), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["InvitingJob"] = relationship("InvitingJob", back_populates="logs")

    __table_args__ = (
        Index("ix_inv_log_job", "job_id", "timestamp"),
    )
