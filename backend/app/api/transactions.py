from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Transaction
from app.schemas import TransactionOut, PaginatedResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=PaginatedResponse[TransactionOut], summary="List Transactions")
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    merchant_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    if merchant_id:
        query = query.filter_by(merchant_id=merchant_id)
    if product_id:
        query = query.filter_by(product_id=product_id)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    total = query.count()
    items = query.order_by(Transaction.transaction_timestamp.desc()).offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{transaction_id}", response_model=TransactionOut, summary="Get Transaction Details")
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter_by(id=transaction_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "TRANSACTION_NOT_FOUND", "message": f"Transaction with ID {transaction_id} not found."}}
        )
    return tx
