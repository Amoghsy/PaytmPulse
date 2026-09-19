"""
Paytm Pulse - Phase 8 Base Action Adapter
Defines standard interfaces and result schemas for all execution adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.action import Action


class AdapterExecutionResult(BaseModel):
    success: bool = Field(..., description="Whether action execution succeeded")
    execution_id: str = Field(..., description="Unique execution identifier")
    action_type: str = Field(..., description="Type of action executed")
    status: str = Field("EXECUTED", description="Execution status: EXECUTED or FAILED")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured execution metadata")
    message: str = Field(..., description="Merchant-friendly execution summary")
    error: Optional[str] = None
    is_mock: bool = True


class BaseActionAdapter(ABC):
    """
    Abstract interface for executing merchant actions.
    Enables zero-friction substitution between mock and official provider integrations.
    """

    @abstractmethod
    def execute(self, action: Action, db: Session) -> AdapterExecutionResult:
        """
        Executes an approved action against the underlying service or database.
        """
        pass
