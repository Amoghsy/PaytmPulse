"""
Paytm Pulse - Phase 8 Execution Schemas
Pydantic data models for execution requests, execution results, retry requests, and history.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ExecutionRequest(BaseModel):
    action_id: str = Field(..., description="Action ID to execute")
    force: bool = Field(False, description="Force retry even if previously attempted")


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str
    execution_id: str
    merchant_id: str
    action_type: str
    status: str  # 'EXECUTED', 'FAILED', 'EXECUTING'
    executed_at: Optional[datetime] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    message: str
    retry_count: int = 0
    failure_reason: Optional[str] = None
    is_mock: bool = True


class RetryExecutionRequest(BaseModel):
    action_id: str


class ActionExecutionStatusResponse(BaseModel):
    action_id: str
    merchant_id: str
    status: str
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    retry_count: int = 0
    failure_reason: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None


class ExecutionHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str
    merchant_id: str
    action_type: str
    status: str
    title: Optional[str] = None
    execution_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
