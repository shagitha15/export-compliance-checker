"""
Common API Schemas & Data Contracts.
"""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = Field(default=True, description="Indicates if operation succeeded")
    message: Optional[str] = Field(default=None, description="Human readable response message")
    data: T = Field(..., description="Payload data")
    meta: Optional[dict[str, Any]] = Field(default=None, description="Request metadata and telemetry")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Descriptive error explanation")
    details: Optional[Any] = Field(default=None, description="Structured diagnostics")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorDetail
