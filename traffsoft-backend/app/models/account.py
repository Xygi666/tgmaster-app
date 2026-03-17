from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(32), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    status = Column(String(32), default="active")  # active / spam_block / banned
    proxy = Column(String(255), nullable=True)
    group_name = Column(String(64), nullable=True)

    tasks_per_day = Column(Integer, default=0)
    tasks_limit = Column(Integer, default=500)

    last_activity_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
