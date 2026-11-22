"""
Pydantic Models and Schemas for Cross-Document Validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT APPLICABLE"


class CheckResult(BaseModel):
    check_id: str = Field(..., description="Unique identifier for the validation rule check")
    rule_name: str = Field(..., description="Human-readable rule name")
    documents_involved: list[str] = Field(..., description="List of document types compared in this check")
    status: ValidationStatus = Field(..., description="Evaluation status: PASS, FAIL, or NOT APPLICABLE")
    field_name: str = Field(..., description="Name of the audited field")
    expected_value: Any = Field(default=None, description="Reference or benchmark value")
    observed_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Values observed in each comparing document",
    )
    discrepancy: Any = Field(default=None, description="Difference or variance detected (if applicable)")
    message: str = Field(..., description="Explanatory audit message or reason for failure/skip")


class IntraDocumentCheckResult(BaseModel):
    document_type: str = Field(..., description="Document type evaluated")
    check_name: str = Field(..., description="Internal validation rule checked")
    status: ValidationStatus = Field(..., description="Evaluation status: PASS or FAIL")
    message: str = Field(..., description="Audit observation")


class ValidationSummary(BaseModel):
    total_checks: int = Field(..., description="Total validation checks executed")
    passed: int = Field(..., description="Number of passed checks")
    failed: int = Field(..., description="Number of failed checks")
    not_applicable: int = Field(..., description="Number of skipped/not applicable checks")


class CrossDocumentValidationResponse(BaseModel):
    audit_id: str = Field(..., description="Unique audit identification UUID")
    audit_timestamp: str = Field(..., description="ISO 8601 audit execution timestamp")
    documents_evaluated: list[str] = Field(..., description="List of document types submitted for evaluation")
    documents_missing: list[str] = Field(..., description="List of standard export document types omitted")
    overall_compliance_status: ValidationStatus = Field(
        ...,
        description="Overall status: PASS if all applicable checks pass, FAIL if any fail",
    )
    summary: ValidationSummary = Field(..., description="Aggregated validation counts")
    intra_document_results: list[IntraDocumentCheckResult] = Field(
        default_factory=list,
        description="Document-specific internal consistency results",
    )
    cross_document_results: list[CheckResult] = Field(
        default_factory=list,
        description="Reconciliation results across multiple documents",
    )
