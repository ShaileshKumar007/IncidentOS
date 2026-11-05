from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolExecutionResult(BaseModel):
    """Structured audit record for all tool invocations."""
    tool_name: str
    incident_id: Optional[str] = None
    agent_id: Optional[str] = None
    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(description="SUCCESS or ERROR")
    duration_ms: float
    result_summary: str
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized API error response format."""
    error_code: str
    message: str
    detail: Optional[Any] = None
