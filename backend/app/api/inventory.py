from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models import Inventory, Product
from app.schemas import InventoryOut

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/{product_id}", response_model=InventoryOut, summary="Get Product Inventory")
def get_inventory(product_id: str, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter_by(product_id=product_id).first()
    if not inventory:
        # Check if product exists
        product = db.query(Product).filter_by(id=product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "PRODUCT_NOT_FOUND", "message": f"Product with ID {product_id} not found."}}
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "INVENTORY_NOT_FOUND", "message": f"Inventory for product ID {product_id} not found."}}
        )
    return inventory
