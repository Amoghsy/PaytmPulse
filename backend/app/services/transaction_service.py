import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.transaction import Transaction
from app.models.base import utc_now, generate_uuid
from app.schemas.event_ingestion import TransactionEventPayload, IngestionResponse
from app.services import redis_service
from app.events.detector import detect_business_events

logger = logging.getLogger("paytm_pulse.transaction_service")


def process_transaction_event(db: Session, payload: TransactionEventPayload) -> IngestionResponse:
    """
    Ingests and processes a single transaction event atomically:
    1. Idempotency deduplication check on external_event_id.
    2. Validates merchant, product, inventory, and customer.
    3. Atomically creates Transaction, reduces Inventory stock, updates Customer totals.
    4. Pushes to Redis cache list & real-time counter metrics.
    5. Runs business event detection rules (Demand Spike, Sales Decline, Stockout Risk).
    """
    # 1. Idempotency Check
    if payload.external_event_id:
        existing_tx = db.query(Transaction).filter(
            Transaction.external_event_id == payload.external_event_id
        ).first()

        if existing_tx:
            logger.info(f"Idempotency hit: external_event_id '{payload.external_event_id}' already processed.")
            return IngestionResponse(
                status="already_processed",
                message="Transaction already ingested previously",
                transaction_id=existing_tx.id,
                external_event_id=existing_tx.external_event_id,
                detected_events=[],
                summary={"merchant_id": existing_tx.merchant_id, "amount": float(existing_tx.amount)}
            )

    # 2. Validation
    merchant = db.query(Merchant).filter(Merchant.id == payload.merchant_id).first()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant with ID '{payload.merchant_id}' not found."
        )

    product = db.query(Product).filter(
        Product.id == payload.product_id,
        Product.merchant_id == payload.merchant_id
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{payload.product_id}' not found for merchant '{payload.merchant_id}'."
        )

    if payload.customer_id:
        customer = db.query(Customer).filter(
            Customer.id == payload.customer_id,
            Customer.merchant_id == payload.merchant_id
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID '{payload.customer_id}' not found for merchant '{payload.merchant_id}'."
            )

    # 3. Calculate Amount & Timestamps
    tx_timestamp = payload.transaction_timestamp or utc_now()
    tx_amount = Decimal(str(round(payload.quantity * payload.unit_price, 2)))

    # 4. Atomic Database Mutations
    tx_id = generate_uuid()
    new_tx = Transaction(
        id=tx_id,
        external_event_id=payload.external_event_id,
        merchant_id=payload.merchant_id,
        product_id=payload.product_id,
        customer_id=payload.customer_id,
        quantity=payload.quantity,
        unit_price=Decimal(str(payload.unit_price)),
        amount=tx_amount,
        payment_method=payload.payment_method,
        transaction_timestamp=tx_timestamp
    )
    db.add(new_tx)

    # Update Inventory
    inventory = db.query(Inventory).filter(
        Inventory.product_id == payload.product_id
    ).first()

    if inventory:
        inventory.current_stock = max(0, inventory.current_stock - payload.quantity)
        inventory.last_restocked_at = inventory.last_restocked_at or utc_now()
    else:
        # Create inventory row if missing
        inventory = Inventory(
            id=generate_uuid(),
            product_id=payload.product_id,
            current_stock=max(0, 10 - payload.quantity),
            reorder_level=5
        )
        db.add(inventory)

    # Update Customer totals if customer_id present
    if payload.customer_id:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if customer:
            customer.purchase_count += 1
            customer.total_spend = Decimal(str(customer.total_spend or 0)) + tx_amount
            customer.last_purchase_at = tx_timestamp

    # 5. Flush DB to assign IDs
    db.flush()

    # 6. Evaluate Business Event Detector Rules
    triggered_events = detect_business_events(
        session=db,
        merchant_id=payload.merchant_id,
        product_id=payload.product_id,
        current_time=tx_timestamp
    )

    # Commit DB Transaction
    db.commit()

    # 7. Push to Redis State Counters & Fast Memory
    tx_summary = {
        "id": tx_id,
        "external_event_id": payload.external_event_id,
        "merchant_id": payload.merchant_id,
        "product_id": payload.product_id,
        "product_name": product.name,
        "quantity": payload.quantity,
        "unit_price": float(payload.unit_price),
        "amount": float(tx_amount),
        "payment_method": payload.payment_method.value,
        "transaction_timestamp": tx_timestamp.isoformat()
    }
    redis_service.push_recent_transaction(payload.merchant_id, tx_summary)
    redis_service.increment_merchant_counter(payload.merchant_id, "daily_sales", float(tx_amount))
    redis_service.increment_merchant_counter(payload.merchant_id, "transaction_count", 1)

    # Phase 11 Fast Memory & Cache Invalidation hooks
    try:
        from app.memory.transaction_memory import TransactionMemory
        from app.memory.cache import IntelligenceCache
        from app.memory.session_memory import SessionMemory
        from app.memory.alert_memory import AlertMemory

        TransactionMemory.push_transaction(payload.merchant_id, tx_summary)
        IntelligenceCache.invalidate_all(payload.merchant_id)
        SessionMemory.update_session(payload.merchant_id, last_action="transaction_ingested")

        for ev in triggered_events:
            AlertMemory.set_alert(
                merchant_id=payload.merchant_id,
                event_id=str(ev.id),
                alert_data={
                    "id": str(ev.id),
                    "event_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                    "severity": ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
                    "payload": ev.payload,
                    "detected_at": ev.detected_at.isoformat() if hasattr(ev.detected_at, "isoformat") else str(ev.detected_at)
                }
            )
            
            # Real-time Proactive Multilingual WhatsApp Alert to Merchant
            try:
                from app.communication.notification_service import NotificationService
                ev_type_str = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
                sev_str = ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity)
                
                details = ev.payload.get("message") if isinstance(ev.payload, dict) and "message" in ev.payload else None
                if not details:
                    if "DEMAND" in ev_type_str:
                        details = f"🚀 Sudden surge in purchases detected for {product.name}! Sales velocity is 2.5x normal."
                    elif "STOCK" in ev_type_str:
                        details = f"⚠️ Low inventory warning: {product.name} is down to {inventory.current_stock} units (below safety reorder level)."
                    elif "DECLINE" in ev_type_str:
                        details = f"📉 Sales volume has dropped below expected baseline for this time window."
                    else:
                        details = f"Telemetry event detected on {product.name}."

                notifications = NotificationService(db)
                notifications.send_business_event_alert(
                    merchant=merchant,
                    event_type=ev_type_str,
                    severity=sev_str,
                    details_message=details,
                    product_id=payload.product_id
                )
            except Exception as notify_err:
                logger.warning(f"WhatsApp alert dispatch non-fatal error: {notify_err}")

    except Exception as mem_err:
        logger.warning(f"Memory / Alert hook non-fatal error: {mem_err}")

    formatted_events = [
        {
            "id": ev.id,
            "event_type": ev.event_type.value,
            "severity": ev.severity.value,
            "payload": ev.payload,
            "detected_at": ev.detected_at.isoformat()
        } for ev in triggered_events
    ]

    return IngestionResponse(
        status="success",
        message="Transaction ingested and processed successfully",
        transaction_id=tx_id,
        external_event_id=payload.external_event_id,
        detected_events=formatted_events,
        summary={
            "merchant_id": payload.merchant_id,
            "product_name": product.name,
            "quantity": payload.quantity,
            "amount": float(tx_amount),
            "remaining_stock": inventory.current_stock
        }
    )
