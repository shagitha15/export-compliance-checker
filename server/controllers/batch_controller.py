"""
Batch Document Ingestion and Consolidated Compliance Controller.
Handles batch validation, independent per-file processing, deduplication,
OCR, automated classification, Gemini extraction, and batch-level compliance reconciliation.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status

from server.compliance.engine import validate_documents
from server.config.settings import get_settings
from server.document_intelligence.classifier import classify_document_type
from server.document_intelligence.extractor import extract_document_data
from server.logging.logger import get_logger
from server.ocr.extractor import extract_text_from_pdf
from server.repositories.document_repository import store_extracted_document
from server.rules.checker import verify_government_rules
from server.schemas.batch import (
    BatchDocumentItem,
    BatchProcessingStatus,
    BatchProcessingSummary,
    BatchUploadResponse,
    DocumentItemStatus,
)
from server.schemas.upload import DocumentType

logger = get_logger("server.controllers.batch")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class BatchController:
    """
    Controller executing multi-document batch uploads and consolidated compliance audits.
    """

    @staticmethod
    async def process_batch_upload(
        files: List[UploadFile],
        document_types: Optional[List[str]] = None,
        org_context: Any | None = None,
    ) -> BatchUploadResponse:
        """
        Processes up to 5 uploaded customs documents in a single request.
        Validates, dedupes, extracts, and reconciles compliance with partial-failure tolerance.
        """
        settings = get_settings()
        max_batch_files = getattr(settings, "MAX_BATCH_FILES", 5)
        max_file_size = getattr(settings, "MAX_FILE_SIZE_BYTES", 25 * 1024 * 1024)

        # 1. Batch Count Validation
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided in batch upload request.",
            )

        if len(files) > max_batch_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Batch upload limit exceeded: Maximum {max_batch_files} documents allowed per batch, "
                    f"but received {len(files)} files."
                ),
            )

        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Initiating batch processing %s with %d files", batch_id, len(files))

        document_results: List[BatchDocumentItem] = []
        extracted_documents_map: dict[str, dict[str, Any]] = {}
        document_storage_paths: dict[str, str] = {}
        document_hashes: dict[str, str] = {}

        seen_filenames: set[str] = set()
        seen_hashes: dict[str, str] = {}  # sha256 -> original filename

        # 2. Process each uploaded document independently
        for idx, file in enumerate(files):
            orig_name = file.filename or f"document_{idx + 1}.pdf"

            # Check 2A: Filename duplicate in this batch
            if orig_name in seen_filenames:
                logger.warning("[%s] Duplicate filename detected: '%s'. Skipping.", batch_id, orig_name)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.DUPLICATE,
                        file_size_bytes=0,
                        error=f"Duplicate filename '{orig_name}' submitted in the same batch. Skipped duplicate.",
                        error_code="DUPLICATE_FILENAME",
                    )
                )
                continue

            seen_filenames.add(orig_name)

            # Read file buffer
            try:
                content = await file.read()
                file_size = len(content)
            except Exception as read_err:
                logger.error("[%s] Failed to read stream for '%s': %s", batch_id, orig_name, read_err)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=0,
                        error=f"Failed to read file stream: {str(read_err)}",
                        error_code="STREAM_READ_ERROR",
                    )
                )
                continue
            finally:
                await file.close()

            # Check 2B: Empty file check
            if file_size == 0:
                logger.warning("[%s] File '%s' is empty (0 bytes).", batch_id, orig_name)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=0,
                        error=f"Uploaded file '{orig_name}' is empty (0 bytes).",
                        error_code="EMPTY_FILE",
                    )
                )
                continue

            # Check 2C: File size limit check
            if file_size > max_file_size:
                logger.warning(
                    "[%s] File '%s' exceeds size limit: %d > %d bytes.",
                    batch_id,
                    orig_name,
                    file_size,
                    max_file_size,
                )
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=(
                            f"File size ({file_size} bytes) exceeds maximum allowed limit of "
                            f"{max_file_size} bytes."
                        ),
                        error_code="FILE_TOO_LARGE",
                    )
                )
                continue

            # Check 2D: Content duplicate check (SHA-256)
            content_hash = hashlib.sha256(content).hexdigest()
            if content_hash in seen_hashes:
                earlier_file = seen_hashes[content_hash]
                logger.warning(
                    "[%s] Duplicate content detected: '%s' is identical to '%s'. Skipping.",
                    batch_id,
                    orig_name,
                    earlier_file,
                )
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.DUPLICATE,
                        file_size_bytes=file_size,
                        error=f"Duplicate file content detected: Identical to '{earlier_file}' in this batch.",
                        error_code="DUPLICATE_CONTENT",
                    )
                )
                continue

            seen_hashes[content_hash] = orig_name
            # Record hash for audit trail

            # Check 2E: Extension check
            ext = Path(orig_name).suffix.lower()
            if ext != ".pdf":
                logger.warning("[%s] Unsupported extension '%s' for '%s'.", batch_id, ext, orig_name)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=f"Invalid file extension '{ext}'. Only '.pdf' files are accepted.",
                        error_code="INVALID_EXTENSION",
                    )
                )
                continue

            # Check 2F: MIME / Content-Type check
            if file.content_type and file.content_type not in ("application/pdf", "application/octet-stream"):
                logger.warning("[%s] Invalid content-type '%s' for '%s'.", batch_id, file.content_type, orig_name)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=f"Invalid content type '{file.content_type}'. Must be 'application/pdf'.",
                        error_code="INVALID_MIME_TYPE",
                    )
                )
                continue

            # Check 2G: PDF Magic Byte (%PDF) header check
            if not content.startswith(b"%PDF"):
                logger.warning("[%s] Missing %%PDF signature in '%s'.", batch_id, orig_name)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error="Corrupted or invalid PDF document (missing %PDF signature).",
                        error_code="CORRUPT_PDF_HEADER",
                    )
                )
                continue

            # Check 2H: PyMuPDF structure readability
            try:
                test_doc = fitz.open(stream=content, filetype="pdf")
                page_count = len(test_doc)
                test_doc.close()
                if page_count == 0:
                    raise ValueError("PDF document contains 0 pages.")
            except Exception as pdf_err:
                logger.warning("[%s] PDF parser failed for '%s': %s", batch_id, orig_name, pdf_err)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=f"Unreadable or corrupted PDF structure: {str(pdf_err)}",
                        error_code="CORRUPT_PDF_STRUCTURE",
                    )
                )
                continue

            # 3. Persist file to storage
            safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(orig_name).stem).strip("_") or "doc"
            unique_filename = f"{safe_stem}_{uuid.uuid4().hex[:10]}.pdf"
            save_path = UPLOAD_DIR / unique_filename

            try:
                with save_path.open("wb") as buffer:
                    buffer.write(content)
            except Exception as save_err:
                logger.error("[%s] Could not save '%s' to disk: %s", batch_id, orig_name, save_err)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=f"Failed to persist file to server storage: {str(save_err)}",
                        error_code="STORAGE_ERROR",
                    )
                )
                continue

            document_hashes[unique_filename] = content_hash
            if org_context:
                try:
                    from server.storage.document_storage import DocumentStorageService

                    storage_path = DocumentStorageService().upload_private_pdf(
                        organization_id=org_context.organization_id,
                        batch_id=batch_id,
                        filename=unique_filename,
                        content=content,
                    )
                    document_storage_paths[unique_filename] = storage_path
                except Exception as storage_err:
                    logger.warning(
                        "[%s] Private Supabase Storage upload skipped for '%s': %s",
                        batch_id,
                        unique_filename,
                        storage_err,
                    )

            # 4. OCR Extraction
            try:
                page_texts = extract_text_from_pdf(save_path)
                combined_text = "\n".join(page_texts.values()) if isinstance(page_texts, dict) else str(page_texts)
            except Exception as ocr_err:
                logger.error("[%s] OCR extraction failed for '%s': %s", batch_id, orig_name, ocr_err)
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        saved_filename=unique_filename,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        error=f"OCR extraction failed: {str(ocr_err)}",
                        error_code="OCR_EXTRACTION_FAILED",
                    )
                )
                continue

            # 5. Resolve Document Type (Explicit or Automated Classification)
            explicit_type_str: Optional[str] = None
            if document_types and idx < len(document_types) and document_types[idx]:
                explicit_type_str = document_types[idx].strip()

            valid_enum_values = {e.value: e for e in DocumentType}
            if explicit_type_str and explicit_type_str in valid_enum_values:
                doc_type_name = valid_enum_values[explicit_type_str].value
            elif explicit_type_str == "Bill of Lading":
                doc_type_name = "Bill of Lading"
            elif (
                "bill of lading" in combined_text.lower()
                or "b/l no" in combined_text.lower()
                or "bill_of_lading" in orig_name.lower()
            ) and "shipping bill" not in combined_text.lower():
                doc_type_name = "Bill of Lading"
            else:
                resolved_doc_type = classify_document_type(text=combined_text, filename=orig_name)
                doc_type_name = resolved_doc_type.value

            # 6. Structured JSON Extraction via Gemini (with scanned PDF & fallback support)
            extraction_method = "gemini_ai"
            fallback_used = False
            item_warning: Optional[str] = None
            item_error_code: Optional[str] = None
            try:
                extract_kwargs: dict[str, Any] = {
                    "document_type": doc_type_name,
                    "pdf_text": page_texts,
                    "source_filename": unique_filename,
                    "save_to_disk": True,
                }
                if not combined_text.strip():
                    extract_kwargs["pdf_bytes"] = content
                extracted_json = extract_document_data(**extract_kwargs)
                meta = extracted_json.get("_extraction_metadata") if isinstance(extracted_json, dict) else None
                if isinstance(meta, dict) and meta.get("fallback_used"):
                    extraction_method = "pymupdf_fallback"
                    fallback_used = True
                    item_error_code = "GEMINI_EXTRACTION_FALLBACK"
                    item_warning = (
                        f"Gemini AI extraction failed ({meta.get('gemini_error', 'unavailable')}); "
                        "populated available fields using PyMuPDF text fallback (non-AI)."
                    )
                    logger.warning(
                        "[%s] Fallback PyMuPDF extraction used for '%s' (%s): %s",
                        batch_id,
                        orig_name,
                        doc_type_name,
                        item_warning,
                    )
            except Exception as ai_err:
                logger.error(
                    "[%s] Gemini extraction failed for '%s' (%s): %s",
                    batch_id,
                    orig_name,
                    doc_type_name,
                    ai_err,
                )
                err_code = getattr(ai_err, "error_code", None) or "GEMINI_EXTRACTION_FAILED"
                document_results.append(
                    BatchDocumentItem(
                        original_filename=orig_name,
                        saved_filename=unique_filename,
                        document_type=doc_type_name,
                        status=DocumentItemStatus.FAILED,
                        file_size_bytes=file_size,
                        extraction_method="failed",
                        fallback_used=False,
                        error=f"Structured intelligence extraction failed: {str(ai_err)}",
                        error_code=err_code,
                    )
                )
                continue

            # 7. Database Persistence (Supabase repository with offline safety)
            try:
                store_extracted_document(
                    filename=unique_filename,
                    document_type=doc_type_name,
                    extracted_data=extracted_json,
                    organization_id=org_context.organization_id if org_context else None,
                    created_by=org_context.user.user_id if org_context else None,
                )
            except Exception as db_err:
                logger.warning(
                    "[%s] Database persistence skipped for '%s': %s. Local extracted copy preserved.",
                    batch_id,
                    unique_filename,
                    db_err,
                )

            # Success item (with explicit provenance if fallback was used)
            document_results.append(
                BatchDocumentItem(
                    original_filename=orig_name,
                    saved_filename=unique_filename,
                    document_type=doc_type_name,
                    status=DocumentItemStatus.SUCCESS,
                    file_size_bytes=file_size,
                    extraction_method=extraction_method,
                    fallback_used=fallback_used,
                    warning=item_warning,
                    error_code=item_error_code,
                    extracted_data=extracted_json,
                )
            )
            extracted_documents_map[doc_type_name] = extracted_json
            logger.info(
                "[%s] Processed document '%s' as '%s' (method=%s)",
                batch_id,
                orig_name,
                doc_type_name,
                extraction_method,
            )

        # 8. Compute Batch Metrics
        successful_cnt = sum(1 for d in document_results if d.status == DocumentItemStatus.SUCCESS)
        failed_cnt = sum(1 for d in document_results if d.status == DocumentItemStatus.FAILED)
        duplicate_cnt = sum(1 for d in document_results if d.status == DocumentItemStatus.DUPLICATE)

        all_standard_types = [e.value for e in DocumentType]
        detected_types = list(extracted_documents_map.keys())
        missing_types = [t for t in all_standard_types if t not in detected_types]

        if successful_cnt == len(document_results) and successful_cnt > 0:
            overall_batch_status = BatchProcessingStatus.SUCCESS
        elif successful_cnt > 0:
            overall_batch_status = BatchProcessingStatus.PARTIAL_SUCCESS
        else:
            overall_batch_status = BatchProcessingStatus.FAILED

        summary = BatchProcessingSummary(
            total_files_received=len(files),
            successful_count=successful_cnt,
            failed_count=failed_cnt,
            duplicate_count=duplicate_cnt,
            detected_document_types=detected_types,
            missing_document_types=missing_types,
        )

        # 9. Downstream Compliance Reconciliation & Statutory Audits
        cross_doc_report = None
        gov_compliance_report = None

        if successful_cnt > 0:
            try:
                cross_doc_report = validate_documents(extracted_documents_map)
            except Exception as val_err:
                logger.error("[%s] Cross-document reconciliation error: %s", batch_id, val_err)

            try:
                gov_compliance_report = verify_government_rules(extracted_documents_map)
            except Exception as gov_err:
                logger.error("[%s] Statutory government rules audit error: %s", batch_id, gov_err)

        logger.info(
            "Batch %s completed: status=%s, success=%d, failed=%d, duplicates=%d",
            batch_id,
            overall_batch_status.value,
            successful_cnt,
            failed_cnt,
            duplicate_cnt,
        )

        response_obj = BatchUploadResponse(
            batch_id=batch_id,
            timestamp=timestamp,
            batch_status=overall_batch_status,
            summary=summary,
            documents=document_results,
            cross_document_validation=cross_doc_report,
            government_compliance=gov_compliance_report,
        )

        if org_context:
            try:
                from server.repositories.audit_repository import AuditRepository

                AuditRepository().save_batch_audit(
                    organization_id=org_context.organization_id,
                    user_id=org_context.user.user_id,
                    batch_response_dict=response_obj.model_dump(mode="json"),
                    document_storage_paths=document_storage_paths,
                    document_hashes=document_hashes,
                )
            except Exception as audit_err:
                logger.warning("[%s] Scoped audit batch DB persistence skipped: %s", batch_id, audit_err)

        return response_obj
