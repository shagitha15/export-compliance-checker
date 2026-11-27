"""
Compliance Controller.
Handles cross-document compliance validation, stored document audits, and statutory government-rule verification.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from server.compliance.engine import validate_documents
from server.logging.logger import get_logger
from server.repositories.document_repository import fetch_extracted_documents
from server.rules.checker import verify_government_rules
from server.schemas.compliance import ComplianceAuditResponse, GovernmentComplianceReport
from server.schemas.validation import (
    CrossDocumentValidationResponse,
    ValidateStoredFilesPayload,
    ValidationDirectPayload,
)

logger = get_logger("server.controllers.compliance")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACTED_DATA_DIR = PROJECT_ROOT / "extracted_data"


class ComplianceController:
    """
    Controller executing compliance validation workflows and statutory regulatory audits.
    """

    @staticmethod
    async def validate_documents(
        payload: ValidationDirectPayload,
    ) -> CrossDocumentValidationResponse:
        """
        Executes two-stage validation (intra-document and cross-document reconciliation) on direct JSON payloads.
        """
        if not payload.documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must include at least one document dictionary under 'documents'.",
            )

        try:
            return validate_documents(payload.documents)
        except Exception as exc:
            logger.error("Cross-document validation engine error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation engine error: {str(exc)}",
            ) from exc

    @staticmethod
    async def validate_stored_documents(
        payload: ValidateStoredFilesPayload,
        org_context: Any | None = None,
    ) -> CrossDocumentValidationResponse:
        """
        Loads extracted document JSONs from Supabase (scoped to organization) and validates them.
        """
        if not payload.filenames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide at least one filename to validate.",
            )

        documents_map: dict[str, dict[str, Any]] = {}

        for fname in payload.filenames:
            clean_name = Path(fname).name
            # 1. Attempt retrieval from Supabase repository strictly scoped to organization
            try:
                records = fetch_extracted_documents(
                    filename=clean_name,
                    organization_id=org_context.organization_id if org_context else None,
                    limit=1,
                )
                if records and "extracted_data" in records[0]:
                    doc_type = (
                        records[0].get("document_type")
                        or records[0]["extracted_data"].get("document_type")
                    )
                    if doc_type:
                        documents_map[doc_type] = records[0]["extracted_data"]
                        continue
            except Exception as exc:
                logger.warning(
                    "Could not fetch '%s' from Supabase: %s.",
                    clean_name,
                    exc,
                )

            # 2. Disk fallback only when running without multi-tenant context
            if org_context is None:
                local_path = EXTRACTED_DATA_DIR / f"{Path(clean_name).stem}_extracted.json"
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
            return validate_documents(documents_map)
        except Exception as exc:
            logger.error("Validation failed for stored documents: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation engine execution failed: {str(exc)}",
            ) from exc

    @staticmethod
    async def verify_statutory_rules(
        payload: ValidationDirectPayload,
    ) -> GovernmentComplianceReport:
        """
        Retrieves statutory export rules semantically and audits shipment documents against Indian mandates.
        """
        if not payload.documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain shipment document data under 'documents'.",
            )

        try:
            return verify_government_rules(payload.documents)
        except Exception as exc:
            logger.error("Government rules verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Government compliance check error: {str(exc)}",
            ) from exc

    @staticmethod
    async def audit_full_shipment(
        payload: ValidationDirectPayload,
    ) -> ComplianceAuditResponse:
        """
        Unified audit endpoint running both cross-document reconciliation and statutory government verification.
        """
        if not payload.documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain shipment document data under 'documents'.",
            )

        try:
            cross_doc_report = validate_documents(payload.documents)
            gov_report = verify_government_rules(payload.documents)
            return ComplianceAuditResponse(
                cross_document_validation=cross_doc_report,
                government_compliance=gov_report,
            )
        except Exception as exc:
            logger.error("Unified shipment audit failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unified compliance audit error: {str(exc)}",
            ) from exc

    @staticmethod
    def generate_pdf_report(payload: Any, org_context: Any | None = None) -> bytes:
        """
        Generates an official A4 PDF compliance certificate using the PyMuPDF report engine.
        Automatically enriches with Task 6 forensic fraud detection when extracted_documents
        are provided and fraud_analysis is omitted, and persists report to private storage
        when org_context & batch_id are supplied.
        """
        from server.reports.pdf_generator import generate_compliance_pdf_report

        try:
            if (
                getattr(payload, "fraud_analysis", None) is None
                and getattr(payload, "extracted_documents", None)
            ):
                from server.forensics.engine import FraudDetectionEngine

                fraud_report = FraudDetectionEngine.audit_extracted_documents(
                    payload.extracted_documents,
                    scenario_title=getattr(payload, "scenario_title", None),
                )
                payload.fraud_analysis = fraud_report.model_dump(mode="json")

            pdf_bytes = generate_compliance_pdf_report(payload)

            batch_id = getattr(payload, "batch_id", None)
            if org_context and batch_id:
                try:
                    from server.repositories.audit_repository import AuditRepository
                    from server.storage.document_storage import DocumentStorageService

                    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(batch_id))
                    report_filename = f"compliance_report_{safe_id}.pdf"
                    storage_path = DocumentStorageService().upload_private_pdf(
                        organization_id=org_context.organization_id,
                        batch_id=str(batch_id),
                        filename=report_filename,
                        content=pdf_bytes,
                    )
                    AuditRepository().save_compliance_report(
                        organization_id=org_context.organization_id,
                        batch_external_id=str(batch_id),
                        generated_by=org_context.user.user_id,
                        report_filename=report_filename,
                        storage_path=storage_path,
                        file_size_bytes=len(pdf_bytes),
                    )
                except Exception as st_err:
                    logger.warning("Private report persistence skipped for '%s': %s", batch_id, st_err)

            return pdf_bytes
        except Exception as exc:
            logger.error("Failed to generate PDF compliance report: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF report generation error: {str(exc)}",
            ) from exc
