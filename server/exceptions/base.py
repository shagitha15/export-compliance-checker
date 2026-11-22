"""
Custom Domain Exceptions.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base class for all domain-specific application exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class DocumentProcessingException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=422, error_code="DOCUMENT_PROCESSING_FAILED", details=details)


class ComplianceValidationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=400, error_code="COMPLIANCE_VALIDATION_FAILED", details=details)


class ResourceNotFoundException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=404, error_code="RESOURCE_NOT_FOUND", details=details)


class IntegrationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, status_code=502, error_code="UPSTREAM_INTEGRATION_ERROR", details=details)
