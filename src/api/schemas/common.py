"""Common API schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None




