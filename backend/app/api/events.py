import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.event_ingestion import TransactionEventPayload, IngestionResponse
from app.schemas.business_event import BusinessEventResponse
from app.models.business_event import BusinessEvent, EventType
from app.services.transaction_service import process_transaction_event

logger = logging.getLogger("paytm_pulse.api.events")

router = APIRouter(prefix="/events", tags=["Events & Pipeline"])


class ConnectionManager:
    """
    Manages WebSocket client connections per merchant for live real-time event streaming.
    """
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, merchant_id: str, websocket: WebSocket):
        await websocket.accept()
        if merchant_id not in self.active_connections:
            self.active_connections[merchant_id] = []
        self.active_connections[merchant_id].append(websocket)
        logger.info(f"WebSocket client connected for merchant {merchant_id}. Total connections: {len(self.active_connections[merchant_id])}")

    def disconnect(self, merchant_id: str, websocket: WebSocket):
        if merchant_id in self.active_connections:
            if websocket in self.active_connections[merchant_id]:
                self.active_connections[merchant_id].remove(websocket)
            if not self.active_connections[merchant_id]:
                del self.active_connections[merchant_id]
        logger.info(f"WebSocket client disconnected for merchant {merchant_id}.")

    async def broadcast_to_merchant(self, merchant_id: str, data: dict):
        if merchant_id in self.active_connections:
            dead_sockets = []
            for connection in self.active_connections[merchant_id]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.warning(f"Error sending WebSocket message: {str(e)}")
                    dead_sockets.append(connection)

            for dead in dead_sockets:
                self.disconnect(merchant_id, dead)


ws_manager = ConnectionManager()


@router.post("/transaction", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_transaction_event(
    payload: TransactionEventPayload,
    db: Session = Depends(get_db)
):
    """
    Real-time transaction ingestion endpoint.
    Validates payload, enforces idempotency on external_event_id, updates database atomically,
    updates Redis state counters, triggers rules engine, and broadcasts events to WebSockets.
    """
    response = process_transaction_event(db, payload)

    # Broadcast detected events to connected WebSocket clients
    if response.detected_events:
        for ev in response.detected_events:
            await ws_manager.broadcast_to_merchant(payload.merchant_id, {
                "type": "BUSINESS_EVENT",
                "data": ev
            })

    # Broadcast transaction summary
    await ws_manager.broadcast_to_merchant(payload.merchant_id, {
        "type": "TRANSACTION_INGESTED",
        "data": response.summary
    })

    return response


@router.post("/transaction/batch", status_code=status.HTTP_200_OK)
async def ingest_transaction_batch(
    payloads: List[TransactionEventPayload],
    db: Session = Depends(get_db)
):
    """
    Batch transaction ingestion endpoint for high-volume bursts.
    Processes each transaction in batch and returns aggregated summary.
    """
    results = []
    total_detected = 0
    for payload in payloads:
        try:
            res = process_transaction_event(db, payload)
            results.append(res)
            total_detected += len(res.detected_events)
        except Exception as e:
            logger.error(f"Batch item failed: {str(e)}")
            results.append({"status": "error", "message": str(e), "merchant_id": payload.merchant_id})

    return {
        "status": "success",
        "processed_count": len(results),
        "total_detected_events": total_detected,
        "details": results
    }


@router.get("", response_model=List[BusinessEventResponse])
def list_business_events(
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=200, description="Max number of events to return"),
    db: Session = Depends(get_db)
):
    """
    Query historical and real-time business events.
    """
    query = db.query(BusinessEvent)
    if merchant_id:
        query = query.filter(BusinessEvent.merchant_id == merchant_id)
    if event_type:
        query = query.filter(BusinessEvent.event_type == event_type)

    events = query.order_by(BusinessEvent.detected_at.desc()).limit(limit).all()
    return events


@router.get("/merchants/{merchant_id}/recent", response_model=List[BusinessEventResponse])
def get_recent_merchant_events(
    merchant_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get recent detected business events for a specific merchant.
    """
    events = db.query(BusinessEvent).filter(
        BusinessEvent.merchant_id == merchant_id
    ).order_by(BusinessEvent.detected_at.desc()).limit(limit).all()
    return events


@router.websocket("/ws/merchants/{merchant_id}")
async def websocket_merchant_events(websocket: WebSocket, merchant_id: str):
    """
    WebSocket endpoint for live real-time event streaming for a merchant.
    """
    await ws_manager.connect(merchant_id, websocket)
    try:
        while True:
            # Keep socket alive and receive client heartbeats/pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(merchant_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection exception: {str(e)}")
        ws_manager.disconnect(merchant_id, websocket)
