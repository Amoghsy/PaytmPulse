from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Product
from app.schemas import ProductOut, PaginatedResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductOut], summary="List Products")
def list_products(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    merchant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if merchant_id:
        query = query.filter_by(merchant_id=merchant_id)

    total = query.count()
    items = query.order_by(Product.name.asc()).offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductOut, summary="Get Product Details")
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PRODUCT_NOT_FOUND", "message": f"Product with ID {product_id} not found."}}
        )
    return product
