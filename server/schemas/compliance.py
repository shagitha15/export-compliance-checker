"""
Pydantic Schemas for Government Regulatory Compliance Verification.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from server.schemas.validation import CrossDocumentValidationResponse




class RegulatoryComplianceStatus(str, Enum):
    """Statutory compliance status."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    ADVISORY = "ADVISORY"


class RegulatoryFinding(BaseModel):
    """Finding for a specific statutory regulation provision."""
    rule_id: str = Field(..., description="Unique code for the statutory rule (e.g. DGFT_FTP2023_P2_05)")
    rule_title: str = Field(..., description="Official title of the regulatory mandate")
    authority: str = Field(..., description="Regulatory body (DGFT, CBIC, RBI, ICEGATE)")
    policy_document: str = Field(..., description="Statute, Act, or Policy reference (e.g. Foreign Trade Policy 2023)")
    para_ref: str = Field(..., description="Specific Section or Paragraph number")
    source_url: str = Field(..., description="Direct hyperlink to the official government source")
    status: RegulatoryComplianceStatus = Field(..., description="COMPLIANT, NON_COMPLIANT, or ADVISORY")
    requirement_summary: str = Field(..., description="Summary of what Indian export law mandates")
    observed_evidence: str = Field(..., description="What was observed or found in the submitted shipment documents")
    action_required: str | None = Field(default=None, description="Remedial action needed if non-compliant")


class GovernmentComplianceSummary(BaseModel):
    """Aggregated metrics for statutory compliance audit."""
    total_rules_evaluated: int = Field(..., description="Total statutory provisions evaluated")
    compliant_count: int = Field(..., description="Provisions satisfied by shipment documentation")
    non_compliant_count: int = Field(..., description="Statutory violations or missing mandates")
    advisory_count: int = Field(..., description="Advisories, guidelines, and compliance recommendations")


class GovernmentComplianceReport(BaseModel):
    """Comprehensive statutory audit report against Indian export regulations."""
    audit_id: str = Field(..., description="Unique audit reference identifier")
    audit_timestamp: str = Field(..., description="ISO 8601 evaluation timestamp")
    hs_codes_evaluated: list[str] = Field(..., description="HS codes evaluated for statutory restrictions")
    destination_country: str | None = Field(default=None, description="Export destination country")
    overall_government_compliance: RegulatoryComplianceStatus = Field(
        ...,
        description="Overall statutory compliance status: COMPLIANT, NON_COMPLIANT, or ADVISORY",
    )
    summary: GovernmentComplianceSummary = Field(..., description="Aggregated statutory compliance metrics")
    findings: list[RegulatoryFinding] = Field(
        default_factory=list,
        description="Detailed regulatory findings with official citations and URLs",
    )


class ComplianceAuditResponse(BaseModel):
    """Unified audit response combining cross-document validation and statutory government rule verification."""
    cross_document_validation: CrossDocumentValidationResponse = Field(
        ...,
        description="Two-stage cross-document reconciliation and intra-document audit report",
    )
    government_compliance: GovernmentComplianceReport = Field(
        ...,
        description="Statutory audit against official Indian export regulations",
    )

