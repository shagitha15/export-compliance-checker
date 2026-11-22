import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status

from ocr import extract_text_from_pdf
from schemas.upload import DocumentType, ExtractionResponse, UploadResponse
from services.gemini_service import extract_document_data
from services.validation import (
    CrossDocumentValidationResponse,
    CrossDocumentValidator,
    validate_documents,
)
from services.rules import GovernmentComplianceReport, verify_government_rules
from supabase_service import fetch_extracted_documents
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Export Customs Documentation Compliance Checker",
    description="API for ingesting, parsing, and extracting structured customs compliance data via Gemini.",
    version="1.1.0",
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Export Customs Documentation Compliance Checker API is running.",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Customs Compliance PDF and Extract Structured Data",
    description=(
        "Uploads a PDF document belonging to one of the 5 allowed customs types, "
        "persists the file, runs OCR, and extracts structured JSON using the Gemini API."
    ),
    tags=["Documents"],
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to be uploaded"),
    document_type: DocumentType = Form(..., description="Allowed export document category"),
):
    # 1. Validate file presence and filename extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload payload.",
        )

    filename_path = Path(file.filename)
    if filename_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{filename_path.suffix}'. Only '.pdf' files are accepted.",
        )

    # 2. Validate MIME / Content Type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{file.content_type}'. Must be 'application/pdf'.",
        )

    # 3. Validate PDF magic byte header (%PDF)
    try:
        header = await file.read(5)
        if not header.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content is not a valid PDF document (missing %PDF signature).",
            )
        await file.seek(0)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inspecting file header: {str(exc)}",
        ) from exc

    # 4. Generate unique, sanitized filename
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename_path.stem).strip("_")
    if not safe_stem:
        safe_stem = "document"

    unique_suffix = uuid.uuid4().hex[:10]
    unique_filename = f"{safe_stem}_{unique_suffix}.pdf"
    destination_path = UPLOAD_DIR / unique_filename

    # 5. Persist file to uploads folder
    try:
        with destination_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to storage: {str(exc)}",
        ) from exc
    finally:
        await file.close()

    # 6. Extract page-wise text using existing OCR module
    try:
        page_texts = extract_text_from_pdf(destination_path)
    except Exception as exc:
        logger.error("OCR extraction failed for %s: %s", destination_path, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from PDF: {str(exc)}",
        ) from exc

    # 7. Extract structured JSON using Gemini API
    try:
        extracted_json = extract_document_data(
            document_type=document_type.value,
            pdf_text=page_texts,
            source_filename=unique_filename,
            save_to_disk=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Gemini structured extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API structured extraction failed: {str(exc)}",
        ) from exc

    # 8. Return structured JSON response
    return UploadResponse(
        filename=unique_filename,
        document_type=document_type,
        upload_status="success",
        file_path=destination_path.as_posix(),
        extracted_data=extracted_json,
    )


@app.post(
    "/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Structured Extraction from PDF",
    description="Uploads a PDF and directly returns the Gemini-extracted structured JSON without requiring prior storage.",
    tags=["Extraction"],
)
async def extract_from_pdf(
    file: UploadFile = File(..., description="PDF file to analyze"),
    document_type: DocumentType = Form(..., description="Target customs document type"),
):
    upload_result = await upload_document(file=file, document_type=document_type)
    return ExtractionResponse(
        filename=upload_result.filename,
        document_type=upload_result.document_type,
        extraction_status="success",
        extracted_data=upload_result.extracted_data or {},
    )


@app.post(
    "/extract-saved/{filename}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Structured Data from an Existing Uploaded PDF",
    description="Runs OCR and Gemini extraction on a PDF that was previously uploaded into the uploads/ directory.",
    tags=["Extraction"],
)
async def extract_saved_document(
    filename: str,
    document_type: DocumentType,
):
    safe_name = Path(filename).name
    file_path = UPLOAD_DIR / safe_name

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{safe_name}' not found in uploads folder.",
        )

    try:
        page_texts = extract_text_from_pdf(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OCR extraction failed: {str(exc)}",
        ) from exc

    try:
        extracted_json = extract_document_data(
            document_type=document_type.value,
            pdf_text=page_texts,
            source_filename=safe_name,
            save_to_disk=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API structured extraction failed: {str(exc)}",
        ) from exc

    return ExtractionResponse(
        filename=safe_name,
        document_type=document_type,
        extraction_status="success",
        extracted_data=extracted_json,
    )


class ValidationDirectPayload(BaseModel):
    documents: dict[str, dict[str, Any]] = Field(
        ...,
        description="Dictionary mapping Document Type (e.g. 'Commercial Invoice', 'Packing List') to extracted JSON data",
    )


class ValidateStoredFilesPayload(BaseModel):
    filenames: list[str] = Field(
        ...,
        description="List of filenames previously processed and saved in Supabase or extracted_data directory",
    )


@app.post(
    "/validate",
    response_model=CrossDocumentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cross-Document Compliance Validation (Direct JSON)",
    description=(
        "Executes two-stage validation (document-specific integrity and cross-document reconciliation) "
        "on provided extracted JSON document data. Returns PASS, FAIL, and NOT APPLICABLE check results."
    ),
    tags=["Validation"],
)
async def validate_extracted_documents(payload: ValidationDirectPayload):
    if not payload.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must include at least one document dictionary under 'documents'.",
        )
    try:
        report = validate_documents(payload.documents)
        return report
    except Exception as exc:
        logger.error("Cross-document validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation engine error: {str(exc)}",
        ) from exc


@app.post(
    "/validate-stored",
    response_model=CrossDocumentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cross-Document Validation for Stored Documents",
    description="Loads extracted document JSONs from Supabase (or extracted_data/ fallback) and executes cross-document reconciliation.",
    tags=["Validation"],
)
async def validate_stored_documents(payload: ValidateStoredFilesPayload):
    if not payload.filenames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide at least one filename to validate.",
        )

    documents_map: dict[str, dict[str, Any]] = {}
    import json

    # 1. Try fetching from Supabase first
    for fname in payload.filenames:
        clean_name = Path(fname).name
        try:
            records = fetch_extracted_documents(filename=clean_name, limit=1)
            if records and "extracted_data" in records[0]:
                doc_type = records[0].get("document_type") or records[0]["extracted_data"].get("document_type")
                if doc_type:
                    documents_map[doc_type] = records[0]["extracted_data"]
                    continue
        except Exception as exc:
            logger.warning("Could not fetch %s from Supabase: %s. Checking local disk.", clean_name, exc)

        # 2. Fallback to local extracted_data/ directory if Supabase record not found
        local_path = Path("extracted_data") / f"{Path(clean_name).stem}_extracted.json"
        if local_path.is_file():
            try:
                with local_path.open("r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    doc_type = local_data.get("document_type")
                    if doc_type:
                        documents_map[doc_type] = local_data
            except Exception as read_exc:
                logger.warning("Failed to read local fallback %s: %s", local_path, read_exc)

    if not documents_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"None of the requested files {payload.filenames} could be found in Supabase or extracted_data/.",
        )

    try:
        report = validate_documents(documents_map)
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation engine execution failed: {str(exc)}",
        ) from exc


@app.post(
    "/verify-government-rules",
    response_model=GovernmentComplianceReport,
    status_code=status.HTTP_200_OK,
    summary="Verify Shipment Against Official Indian Government Export Regulations",
    description=(
        "Retrieves statutory export rules semantically from the Pinecone vector index "
        "(DGFT FTP 2023, CBIC Customs Act, RBI FEMA, SCOMET) and audits shipment documents "
        "against government mandates, providing official citations and source URLs."
    ),
    tags=["Government Regulations"],
)
async def verify_statutory_rules(payload: ValidationDirectPayload):
    if not payload.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain shipment document data under 'documents'.",
        )
    try:
        report = verify_government_rules(payload.documents)
        return report
    except Exception as exc:
        logger.error("Government rules verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Government compliance check error: {str(exc)}",
        ) from exc
