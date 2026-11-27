"""
Document Ingestion & AI Extraction API Routes (v1).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from server.auth.dependencies import require_workflow_context
from server.auth.models import OrganizationContext, WRITER_ROLES
from server.controllers.batch_controller import BatchController
from server.controllers.document_controller import DocumentController
from server.schemas.batch import BatchUploadResponse
from server.schemas.upload import DocumentType, ExtractionResponse, UploadResponse


router = APIRouter(prefix="/documents", tags=["Documents & Extraction"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Customs Compliance PDF and Extract Structured Data",
    description=(
        "Uploads a PDF document belonging to one of the 5 allowed customs types, "
        "persists the file, runs OCR, and extracts structured JSON using the Gemini API."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to be uploaded"),
    document_type: DocumentType = Form(..., description="Allowed export document category"),
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> UploadResponse:
    """
    Ingests PDF document, runs OCR, extracts typed structured data via Gemini, and stores record.
    """
    return await DocumentController.upload_document(
        file=file,
        document_type=document_type,
        org_context=org_context,
    )


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Structured Extraction from PDF",
    description="Uploads a PDF and directly returns the Gemini-extracted structured JSON without requiring prior storage.",
)
async def extract_from_pdf(
    file: UploadFile = File(..., description="PDF file to analyze"),
    document_type: DocumentType = Form(..., description="Target customs document type"),
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> ExtractionResponse:
    """
    Directly extracts structured JSON from an uploaded PDF stream.
    """
    return await DocumentController.extract_from_pdf(
        file=file,
        document_type=document_type,
        org_context=org_context,
    )


@router.post(
    "/extract-saved/{filename}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Structured Data from an Existing Uploaded PDF",
    description="Runs OCR and Gemini extraction on a PDF that was previously uploaded into the uploads/ directory.",
)
async def extract_saved_document(
    filename: str,
    document_type: DocumentType,
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> ExtractionResponse:
    """
    Executes OCR and Gemini extraction on an existing document in the uploads repository.
    """
    return await DocumentController.extract_saved_document(
        filename=filename,
        document_type=document_type,
        org_context=org_context,
    )


@router.post(
    "/batch-upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Ingestion and Consolidated Compliance Verification (Up to 5 Documents)",
    description=(
        "Uploads up to 5 export customs PDF documents simultaneously in a single request. "
        "Validates headers, structure, and sizes; executes OCR and Gemini intelligence; "
        "and produces consolidated cross-document reconciliation and statutory compliance results. "
        "Resilient against partial failures."
    ),
)
async def batch_upload_documents(
    files: List[UploadFile] = File(
        ...,
        description="Up to 5 export customs documents (PDF format, max 25MB each)",
    ),
    document_types: Optional[List[str]] = Form(
        default=None,
        description="Optional list of declared document types corresponding to files",
    ),
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> BatchUploadResponse:
    """
    Consolidated 5-document batch ingestion, OCR extraction, and multi-stage compliance verification.
    """
    return await BatchController.process_batch_upload(
        files=files,
        document_types=document_types,
        org_context=org_context,
    )


@router.post(
    "/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Upload Alias",
    description="Convenience route alias for /batch-upload.",
    include_in_schema=False,
)
async def batch_upload_alias(
    files: List[UploadFile] = File(...),
    document_types: Optional[List[str]] = Form(default=None),
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> BatchUploadResponse:
    """
    Convenience alias for batch upload.
    """
    return await BatchController.process_batch_upload(
        files=files,
        document_types=document_types,
        org_context=org_context,
    )

