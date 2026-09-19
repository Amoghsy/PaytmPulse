"""
Paytm Pulse - Phase 8 Execution Exceptions
"""


class ExecutionError(Exception):
    """Base exception for action execution pipeline."""
    pass


class ActionValidationError(ExecutionError):
    """Raised when an action fails pre-execution validation."""
    pass


class ActionNotApprovedError(ExecutionError):
    """Raised when attempting to execute an action that is not in APPROVED status."""
    pass


class ActionAlreadyExecutedError(ExecutionError):
    """Raised when attempting to execute an action that has already succeeded."""
    pass


class ExecutionLockError(ExecutionError):
    """Raised when failing to acquire the distributed execution lock."""
    pass


class ActionRetryExhaustedError(ExecutionError):
    """Raised when max retry attempts have been reached."""
    pass
