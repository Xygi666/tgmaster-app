from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountRead

router = APIRouter()


@router.get("/", response_model=List[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    group_filter: Optional[str] = Query(None, alias="group"),
):
    query = db.query(Account)
    if status_filter:
        query = query.filter(Account.status == status_filter)
    if group_filter:
        query = query.filter(Account.group_name == group_filter)
    return query.order_by(Account.id).all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.phone == payload.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Аккаунт с таким номером уже существует",
        )
    account = Account(**payload.dict())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аккаунт не найден")
    db.delete(account)
    db.commit()
    return
