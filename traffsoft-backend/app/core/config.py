from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "TraffSoft Backend"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./traffsoft.db"

    JWT_SECRET_KEY: str = "CHANGE_ME_SUPER_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = 60 * 24

    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_SESSION_NAME: str = "tg_session"

    class Config:
        env_file = ".env"
        case_sensitive = True


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres")


def get_async_engine(url: str):
    from sqlalchemy.ext.asyncio import create_async_engine
    return create_async_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def get_sync_engine(url: str):
    from sqlalchemy import create_engine
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
