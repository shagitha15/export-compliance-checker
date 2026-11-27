"""
Pydantic Schemas for 5-Document Batch Upload and Consolidated Compliance Ingestion.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from server.schemas.compliance import GovernmentComplianceReport
from server.schemas.validation import CrossDocumentValidationResponse


class BatchProcessingStatus(str, Enum):
    """Aggregated processing status for the batch upload."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class DocumentItemStatus(str, Enum):
    """Processing status of an individual document in a batch."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
    SKIPPED = "SKIPPED"


class BatchDocumentItem(BaseModel):
    """Individual document outcome within a batch upload."""
    original_filename: str = Field(..., description="Original client-supplied filename")
    saved_filename: str | None = Field(default=None, description="Unique filename assigned in server storage")
    document_type: str | None = Field(default=None, description="Classified or declared customs document type")
    status: DocumentItemStatus = Field(..., description="Individual document processing status")
    file_size_bytes: int = Field(default=0, description="Size of the uploaded document in bytes")
    extraction_method: str | None = Field(
        default=None,
        description="Extraction engine used ('gemini_ai' or 'pymupdf_fallback')",
    )
    fallback_used: bool = Field(
        default=False,
        description="True when PyMuPDF fallback extraction was used after Gemini AI failure",
    )
    warning: str | None = Field(
        default=None,
        description="Non-fatal warning (for example, Gemini failure triggering fallback extraction)",
    )
    extracted_data: dict[str, Any] | None = Field(
        default=None,
        description="Structured JSON extracted by Gemini API or fallback parser (if processing succeeded)",
    )
    error: str | None = Field(default=None, description="Detailed error description if processing failed")
    error_code: str | None = Field(default=None, description="Machine-readable error category code")


class BatchProcessingSummary(BaseModel):
    """Consolidated summary metrics for a batch upload operation."""
    total_files_received: int = Field(..., description="Total files submitted in the batch payload")
    successful_count: int = Field(..., description="Number of files successfully parsed, extracted, and stored")
    failed_count: int = Field(..., description="Number of files that failed validation, OCR, or extraction")
    duplicate_count: int = Field(..., description="Number of duplicate files identified and skipped")
    detected_document_types: list[str] = Field(
        default_factory=list,
        description="List of distinct customs document types successfully processed",
    )
    missing_document_types: list[str] = Field(
        default_factory=list,
        description="Standard export document types omitted from this batch",
    )


class BatchUploadResponse(BaseModel):
    """Consolidated API response for a multi-document batch upload."""
    batch_id: str = Field(..., description="Unique batch identification UUID")
    timestamp: str = Field(..., description="ISO 8601 execution timestamp")
    batch_status: BatchProcessingStatus = Field(
        ...,
        description="Overall batch status: SUCCESS (all passed), PARTIAL_SUCCESS (some passed), or FAILED (all failed)",
    )
    summary: BatchProcessingSummary = Field(..., description="Aggregated processing metrics")
    documents: list[BatchDocumentItem] = Field(..., description="Detailed outcomes for each uploaded document")
    cross_document_validation: CrossDocumentValidationResponse | None = Field(
        default=None,
        description="Two-stage cross-document reconciliation results evaluated across successfully parsed documents",
    )
    government_compliance: GovernmentComplianceReport | None = Field(
        default=None,
        description="Statutory audit against official Indian export regulations",
    )
