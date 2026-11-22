from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    COMMERCIAL_INVOICE = "Commercial Invoice"
    PACKING_LIST = "Packing List"
    PURCHASE_ORDER = "Purchase Order"
    SHIPPING_BILL = "Shipping Bill"
    CERTIFICATE_OF_ORIGIN = "Certificate of Origin"


class UploadResponse(BaseModel):
    filename: str = Field(..., description="Unique filename assigned to the saved PDF")
    document_type: DocumentType = Field(..., description="Validated customs document type")
    upload_status: str = Field(..., description="Status of the upload operation")
    file_path: str = Field(..., description="Path where the file is stored")
    extracted_data: dict[str, Any] | None = Field(
        default=None,
        description="Structured JSON data extracted by Gemini API",
    )


class ExtractionResponse(BaseModel):
    filename: str = Field(..., description="Target PDF filename")
    document_type: DocumentType = Field(..., description="Customs document category")
    extraction_status: str = Field(..., description="Status of the Gemini extraction")
    extracted_data: dict[str, Any] = Field(..., description="Structured JSON extracted by Gemini")
