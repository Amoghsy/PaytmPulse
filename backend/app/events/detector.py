import os
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models.business_event import BusinessEvent, EventType, EventSeverity
from app.models.base import utc_now, generate_uuid
from app.events.rules import evaluate_demand_spike, evaluate_sales_decline, evaluate_stockout_risk

load_dotenv()

logger = logging.getLogger("paytm_pulse.events.detector")
COOLDOWN_MINUTES = int(os.getenv("EVENT_COOLDOWN_MINUTES", 15))


def detect_business_events(session: Session, merchant_id: str, product_id: str = None, current_time: datetime = None) -> list[BusinessEvent]:
    """
    Evaluates rule engine checks (Demand Spike, Sales Decline, Stockout Risk) for a merchant.
    Applies 15-minute cooldown deduplication: updates active event if triggered within COOLDOWN_MINUTES.
    Returns list of BusinessEvent model instances created or updated.
    """
    if current_time is None:
        current_time = utc_now()

    cooldown_cutoff = current_time - timedelta(minutes=COOLDOWN_MINUTES)
    detected_events = []

    # Rule 1: Demand Spike
    spike_triggered, spike_data = evaluate_demand_spike(session, merchant_id, current_time)
    if spike_triggered:
        event = _save_or_update_event(
            session=session,
            merchant_id=merchant_id,
            event_type=spike_data["event_type"],
            severity=spike_data["severity"],
            payload=spike_data["payload"],
            cooldown_cutoff=cooldown_cutoff,
            current_time=current_time
        )
        detected_events.append(event)

    # Rule 2: Sales Decline
    decline_triggered, decline_data = evaluate_sales_decline(session, merchant_id, current_time)
    if decline_triggered:
        event = _save_or_update_event(
            session=session,
            merchant_id=merchant_id,
            event_type=decline_data["event_type"],
            severity=decline_data["severity"],
            payload=decline_data["payload"],
            cooldown_cutoff=cooldown_cutoff,
            current_time=current_time
        )
        detected_events.append(event)

    # Rule 3: Stockout Risk
    if product_id:
        stock_triggered, stock_data = evaluate_stockout_risk(session, merchant_id, product_id)
        if stock_triggered:
            event = _save_or_update_event(
                session=session,
                merchant_id=merchant_id,
                event_type=stock_data["event_type"],
                severity=stock_data["severity"],
                payload=stock_data["payload"],
                cooldown_cutoff=cooldown_cutoff,
                current_time=current_time
            )
            detected_events.append(event)

    return detected_events


def _save_or_update_event(
    session: Session,
    merchant_id: str,
    event_type: EventType,
    severity: EventSeverity,
    payload: dict,
    cooldown_cutoff: datetime,
    current_time: datetime
) -> BusinessEvent:
    """
    Deduplicates events by updating payload/detected_at if an event of the same type
    for the same merchant occurred within COOLDOWN_MINUTES.
    """
    existing_event = session.query(BusinessEvent).filter(
        BusinessEvent.merchant_id == merchant_id,
        BusinessEvent.event_type == event_type,
        BusinessEvent.detected_at >= cooldown_cutoff
    ).order_by(BusinessEvent.detected_at.desc()).first()

    if existing_event:
        logger.info(f"Cooldown active ({COOLDOWN_MINUTES}m) for {event_type} on merchant {merchant_id}. Updating event {existing_event.id}.")
        existing_event.payload = payload
        existing_event.severity = severity
        existing_event.detected_at = current_time
        session.flush()
        return existing_event
    else:
        new_event = BusinessEvent(
            id=generate_uuid(),
            merchant_id=merchant_id,
            event_type=event_type,
            severity=severity,
            source="rule_engine",
            payload=payload,
            detected_at=current_time,
            processed=False
        )
        session.add(new_event)
        session.flush()
        logger.info(f"Created new BusinessEvent {new_event.id} ({event_type}) for merchant {merchant_id}.")
        return new_event
