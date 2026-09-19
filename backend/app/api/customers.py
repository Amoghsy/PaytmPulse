from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Customer
from app.schemas import CustomerOut, PaginatedResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=PaginatedResponse[CustomerOut], summary="List Customers")
def list_customers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    merchant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Customer)
    if merchant_id:
        query = query.filter_by(merchant_id=merchant_id)

    total = query.count()
    items = query.order_by(Customer.total_spend.desc()).offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{customer_id}", response_model=CustomerOut, summary="Get Customer Details")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "CUSTOMER_NOT_FOUND", "message": f"Customer with ID {customer_id} not found."}}
        )
    return customer
