from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountRead

router = APIRouter()


@router.get("/", response_model=List[AccountRead])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    group_filter: Optional[str] = Query(None, alias="group"),
):
    query = select(Account)
    if status_filter:
        query = query.where(Account.status == status_filter)
    if group_filter:
        query = query.where(Account.group_name == group_filter)
    query = query.order_by(Account.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.phone == payload.phone))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Аккаунт с таким номером уже существует",
        )
    account = Account(**payload.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аккаунт не найден")
    await db.delete(account)
    await db.commit()
    return None
