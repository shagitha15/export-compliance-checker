"""
Cross-Document Validation Engine Orchestrator.
Coordinates Stage 1 (Intra-Document) and Stage 2 (Cross-Document) reconciliation audits.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from server.compliance.cross_document import CROSS_DOCUMENT_RULES
from server.compliance.intra_document import run_intra_document_validation
from server.schemas.validation import (
    CheckResult,
    CrossDocumentValidationResponse,
    IntraDocumentCheckResult,
    ValidationStatus,
    ValidationSummary,
)

ALL_EXPORT_DOCUMENTS = [
    "Commercial Invoice",
    "Packing List",
    "Purchase Order",
    "Shipping Bill",
    "Certificate of Origin",
]


class CrossDocumentValidator:
    """
    Orchestrates intra-document integrity auditing and cross-document reconciliation
    across all submitted export customs documents.
    """

    def __init__(self, document_types: list[str] | None = None) -> None:
        self.standard_documents = document_types or ALL_EXPORT_DOCUMENTS

    def validate(self, documents: dict[str, dict[str, Any]]) -> CrossDocumentValidationResponse:
        """
        Executes the two-stage validation pipeline on the provided document dictionary.

        Args:
            documents: Dict mapping document type name (e.g. 'Commercial Invoice')
                       to its extracted JSON data.

        Returns:
            CrossDocumentValidationResponse: Complete structured validation audit report.
        """
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        submitted_types = [doc_type for doc_type in documents.keys() if doc_type in self.standard_documents]
        missing_types = [doc_type for doc_type in self.standard_documents if doc_type not in documents]

        # Stage 1: Document-Specific (Intra-Document) Integrity Checks
        intra_results: list[IntraDocumentCheckResult] = []
        for doc_type, doc_data in documents.items():
            if isinstance(doc_data, dict):
                checks = run_intra_document_validation(doc_type, doc_data)
                intra_results.extend(checks)

        # Stage 2: Cross-Document (Inter-Document) Reconciliation Checks
        cross_results: list[CheckResult] = []
        for rule_fn in CROSS_DOCUMENT_RULES:
            check_result = rule_fn(documents)
            cross_results.append(check_result)

        # Compute Summary Statistics
        all_statuses = [r.status for r in intra_results] + [r.status for r in cross_results]
        passed_count = sum(1 for s in all_statuses if s == ValidationStatus.PASS)
        failed_count = sum(1 for s in all_statuses if s == ValidationStatus.FAIL)
        na_count = sum(1 for s in all_statuses if s == ValidationStatus.NOT_APPLICABLE)
        total_count = len(all_statuses)

        overall_status = ValidationStatus.FAIL if failed_count > 0 else ValidationStatus.PASS

        summary = ValidationSummary(
            total_checks=total_count,
            passed=passed_count,
            failed=failed_count,
            not_applicable=na_count,
        )

        return CrossDocumentValidationResponse(
            audit_id=audit_id,
            audit_timestamp=timestamp,
            documents_evaluated=submitted_types,
            documents_missing=missing_types,
            overall_compliance_status=overall_status,
            summary=summary,
            intra_document_results=intra_results,
            cross_document_results=cross_results,
        )


def validate_documents(documents: dict[str, dict[str, Any]]) -> CrossDocumentValidationResponse:
    """Convenience helper function to run validation directly."""
    validator = CrossDocumentValidator()
    return validator.validate(documents)
