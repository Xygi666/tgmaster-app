from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserUpdate, UserRead

router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not credentials:
        return None
    token = credentials.credentials
    user_id = decode_access_token(token)
    if not user_id:
        return None
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user


async def get_current_active_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return user


async def get_current_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Доступ только для администраторов")
    return user


@router.post("/register", response_model=UserRead)
async def register_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    total = await db.scalar(select(func.count(User.id))) or 0
    if total > 0:
        if not current_user or current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Только администратор может создавать пользователей")

    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    role = "admin" if total == 0 else payload.role
    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")

    expires_minutes = 60 * 24 * 7 if payload.remember_me else 60 * 24
    token = create_access_token(subject=str(user.id), expires_minutes=expires_minutes)

    user.last_login_at = datetime.utcnow()
    await db.commit()

    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_active_user)):
    return user


@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await db.delete(user)
    await db.commit()
    return {"status": "deleted", "id": user_id}
