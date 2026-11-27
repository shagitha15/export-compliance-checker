"""
Document Controller.
Handles document uploads, PDF validation, OCR text extraction, and Gemini structured data intelligence.
"""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from server.config.settings import get_settings
from server.document_intelligence.extractor import extract_document_data
from server.logging.logger import get_logger
from server.ocr.extractor import extract_text_from_pdf
from server.repositories.document_repository import store_extracted_document
from server.schemas.upload import DocumentType, ExtractionResponse, UploadResponse

logger = get_logger("server.controllers.document")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentController:
    """
    Controller managing document lifecycle: validation, storage, OCR, and AI extraction.
    """

    @staticmethod
    async def upload_document(
        file: UploadFile,
        document_type: DocumentType,
        org_context: Any | None = None,
    ) -> UploadResponse:
        """
        Validates, saves, extracts text via OCR, and parses structured JSON via Gemini.
        """
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
        if file.content_type not in ("application/pdf", "application/octet-stream"):
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

        # 6. Extract page-wise text using OCR module
        try:
            page_texts = extract_text_from_pdf(destination_path)
        except Exception as exc:
            logger.error("OCR extraction failed for %s: %s", destination_path, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to extract text from PDF: {str(exc)}",
            ) from exc

        # 7. Extract structured JSON using Gemini API (with fallback provenance)
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

        meta = extracted_json.get("_extraction_metadata") if isinstance(extracted_json, dict) else None
        fallback_used = bool(isinstance(meta, dict) and meta.get("fallback_used"))
        extraction_method = "pymupdf_fallback" if fallback_used else "gemini_ai"
        upload_status = "fallback_pymupdf" if fallback_used else "success"
        warning = (
            f"Gemini AI extraction failed ({meta.get('gemini_error', 'unavailable')}); "
            "used PyMuPDF text fallback extraction (non-AI)."
            if fallback_used
            else None
        )

        # 8. Attempt database & private storage persistence
        if org_context:
            try:
                from server.storage.document_storage import DocumentStorageService

                pdf_bytes = destination_path.read_bytes()
                DocumentStorageService().upload_private_pdf(
                    organization_id=org_context.organization_id,
                    batch_id="single_uploads",
                    filename=unique_filename,
                    content=pdf_bytes,
                )
            except Exception as st_exc:
                logger.warning("Private storage upload skipped for '%s': %s", unique_filename, st_exc)

        try:
            store_extracted_document(
                filename=unique_filename,
                document_type=document_type.value,
                extracted_data=extracted_json,
                organization_id=org_context.organization_id if org_context else None,
                created_by=org_context.user.user_id if org_context else None,
            )
        except Exception as db_exc:
            logger.warning(
                "Could not persist extracted document '%s' to database: %s. Local copy preserved.",
                unique_filename,
                db_exc,
            )

        # 9. Return structured response
        return UploadResponse(
            filename=unique_filename,
            document_type=document_type,
            upload_status=upload_status,
            extraction_method=extraction_method,
            fallback_used=fallback_used,
            warning=warning,
            file_path=destination_path.as_posix(),
            extracted_data=extracted_json,
        )

    @staticmethod
    async def extract_from_pdf(
        file: UploadFile,
        document_type: DocumentType,
        org_context: Any | None = None,
    ) -> ExtractionResponse:
        """
        Direct structured extraction from uploaded PDF without requiring prior storage.
        """
        upload_result = await DocumentController.upload_document(
            file=file,
            document_type=document_type,
            org_context=org_context,
        )
        return ExtractionResponse(
            filename=upload_result.filename,
            document_type=upload_result.document_type,
            extraction_status="fallback_pymupdf" if upload_result.fallback_used else "success",
            extraction_method=upload_result.extraction_method,
            fallback_used=upload_result.fallback_used,
            warning=upload_result.warning,
            extracted_data=upload_result.extracted_data or {},
        )

    @staticmethod
    async def extract_saved_document(
        filename: str,
        document_type: DocumentType,
        org_context: Any | None = None,
    ) -> ExtractionResponse:
        """
        Extracts structured JSON data from a previously uploaded PDF in the storage directory.
        """
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

        try:
            store_extracted_document(
                filename=safe_name,
                document_type=document_type.value,
                extracted_data=extracted_json,
            )
        except Exception as db_exc:
            logger.warning(
                "Could not persist saved document '%s' to database: %s. Local copy preserved.",
                safe_name,
                db_exc,
            )

        meta = extracted_json.get("_extraction_metadata") if isinstance(extracted_json, dict) else None
        fallback_used = bool(isinstance(meta, dict) and meta.get("fallback_used"))
        extraction_method = "pymupdf_fallback" if fallback_used else "gemini_ai"
        warning = (
            f"Gemini AI extraction failed ({meta.get('gemini_error', 'unavailable')}); "
            "used PyMuPDF text fallback extraction (non-AI)."
            if fallback_used
            else None
        )

        return ExtractionResponse(
            filename=safe_name,
            document_type=document_type,
            extraction_status="fallback_pymupdf" if fallback_used else "success",
            extraction_method=extraction_method,
            fallback_used=fallback_used,
            warning=warning,
            extracted_data=extracted_json,
        )

    @staticmethod
    async def batch_upload(
        files: list[UploadFile],
        document_types: list[str] | None = None,
    ):
        """
        Delegates multi-document batch uploads to BatchController.
        """
        from server.controllers.batch_controller import BatchController
        return await BatchController.process_batch_upload(files=files, document_types=document_types)

