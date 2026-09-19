from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models import Merchant, Product, Customer, Transaction, Inventory
from app.schemas import (
    MerchantOut, MerchantSummary,
    ProductOut, CustomerOut, TransactionOut, MerchantInventoryItem,
    PaginatedResponse, ErrorResponse
)

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get("/", response_model=PaginatedResponse[MerchantOut], summary="List Merchants")
@router.get("", response_model=PaginatedResponse[MerchantOut], include_in_schema=False)
def list_merchants(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    total = db.query(Merchant).count()
    items = db.query(Merchant).order_by(Merchant.created_at.asc()).offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}/summary", response_model=MerchantSummary, summary="Get Merchant Business Summary")
def get_merchant_summary(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )

    total_products = db.query(Product).filter_by(merchant_id=merchant_id).count()
    total_customers = db.query(Customer).filter_by(merchant_id=merchant_id).count()
    total_transactions = db.query(Transaction).filter_by(merchant_id=merchant_id).count()
    
    revenue_result = db.query(func.sum(Transaction.amount)).filter_by(merchant_id=merchant_id).scalar()
    total_revenue = float(revenue_result or 0.0)

    return MerchantSummary(
        merchant_id=merchant.id,
        shop_name=merchant.shop_name,
        category=merchant.category.value if hasattr(merchant.category, 'value') else str(merchant.category),
        location=merchant.location,
        total_products=total_products,
        total_customers=total_customers,
        total_transactions=total_transactions,
        total_revenue=total_revenue
    )


@router.get("/{merchant_id}/transactions", response_model=PaginatedResponse[TransactionOut], summary="Get Merchant Transactions")
def get_merchant_transactions(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )

    query = db.query(Transaction).filter_by(merchant_id=merchant_id)

    if product_id:
        query = query.filter_by(product_id=product_id)
    if start_date:
        query = query.filter(Transaction.transaction_timestamp >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_timestamp <= end_date)

    total = query.count()
    items = query.order_by(Transaction.transaction_timestamp.desc()).offset(offset).limit(limit).all()

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}/inventory", response_model=List[MerchantInventoryItem], summary="Get Merchant Inventory")
def get_merchant_inventory(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )

    products = db.query(Product).filter_by(merchant_id=merchant_id).all()
    inventory_items = []
    for prod in products:
        inv = db.query(Inventory).filter_by(product_id=prod.id).first()
        inventory_items.append(MerchantInventoryItem(
            product_id=prod.id,
            product_name=prod.name,
            category=prod.category,
            current_stock=inv.current_stock if inv else prod.current_stock,
            reorder_level=inv.reorder_level if inv else prod.reorder_level,
            maximum_stock=inv.maximum_stock if inv else 100,
            price=float(prod.price),
            average_daily_sales=float(prod.average_daily_sales),
            last_restocked_at=inv.last_restocked_at if inv else None
        ))

    return inventory_items


@router.get("/{merchant_id}/customers", response_model=PaginatedResponse[CustomerOut], summary="Get Merchant Customers")
def get_merchant_customers(
    merchant_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )

    query = db.query(Customer).filter_by(merchant_id=merchant_id)
    total = query.count()
    items = query.order_by(Customer.total_spend.desc()).offset(offset).limit(limit).all()

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}", response_model=MerchantOut, summary="Get Merchant Details")
def get_merchant(merchant_id: str, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )
    return merchant


@router.put("/{merchant_id}/phone", response_model=MerchantOut, summary="Update Merchant Phone Number for Testing")
def update_merchant_phone(
    merchant_id: str,
    phone: str = Query(..., description="New WhatsApp phone number with country code, e.g. '919876543210'"),
    db: Session = Depends(get_db)
):
    """
    Updates the phone number for a merchant to your real WhatsApp test phone.
    """
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "MERCHANT_NOT_FOUND", "message": f"Merchant with ID {merchant_id} not found."}}
        )
    cleaned = "".join(ch for ch in phone if ch.isdigit())
    merchant.phone = cleaned
    db.commit()
    db.refresh(merchant)
    return merchant

