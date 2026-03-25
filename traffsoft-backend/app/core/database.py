from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings, _is_postgres

Base = declarative_base()

_is_pg = _is_postgres(settings.DATABASE_URL)

if _is_pg:
    _async_engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    async_session_maker = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    _sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql", "postgresql+psycopg2", 1),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
else:
    _async_engine = create_async_engine(
        "sqlite+aiosqlite:///./traffsoft.db",
        connect_args={"check_same_thread": False},
    )
    async_session_maker = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    _sync_engine = create_engine(
        "sqlite:///./traffsoft.db",
        connect_args={"check_same_thread": False},
    )

sync_session_maker = sessionmaker(autocommit=False, autoflush=False, bind=_sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
