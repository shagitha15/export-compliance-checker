"""
Document Upload and Ingestion Pydantic Schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported export customs document classifications."""
    COMMERCIAL_INVOICE = "Commercial Invoice"
    PACKING_LIST = "Packing List"
    PURCHASE_ORDER = "Purchase Order"
    SHIPPING_BILL = "Shipping Bill"
    CERTIFICATE_OF_ORIGIN = "Certificate of Origin"


class UploadResponse(BaseModel):
    """Response payload for document uploads."""
    filename: str = Field(..., description="Unique filename assigned to the saved PDF")
    document_type: DocumentType = Field(..., description="Validated customs document type")
    upload_status: str = Field(..., description="Status of the upload operation")
    extraction_method: str | None = Field(default=None, description="'gemini_ai' or 'pymupdf_fallback'")
    fallback_used: bool = Field(default=False, description="True if PyMuPDF fallback extraction was used")
    warning: str | None = Field(default=None, description="Warning message if fallback extraction occurred")
    file_path: str = Field(..., description="Path where the file is stored")
    extracted_data: dict[str, Any] | None = Field(
        default=None,
        description="Structured JSON data extracted by Gemini API or fallback parser",
    )


class ExtractionResponse(BaseModel):
    """Response payload for direct document text extraction."""
    filename: str = Field(..., description="Target PDF filename")
    document_type: DocumentType = Field(..., description="Customs document category")
    extraction_status: str = Field(..., description="Status of the extraction")
    extraction_method: str | None = Field(default=None, description="'gemini_ai' or 'pymupdf_fallback'")
    fallback_used: bool = Field(default=False, description="True if PyMuPDF fallback extraction was used")
    warning: str | None = Field(default=None, description="Warning message if fallback extraction occurred")
    extracted_data: dict[str, Any] = Field(..., description="Structured JSON extracted by Gemini or fallback parser")
