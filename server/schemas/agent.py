"""
Pydantic Schemas for LangGraph Customs Compliance AI Agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from server.schemas.compliance import GovernmentComplianceReport
from server.schemas.fraud import FraudAnalysisReport
from server.schemas.validation import CrossDocumentValidationResponse


class AgentAnalyzeRequest(BaseModel):
    """Payload to trigger an end-to-end LangGraph agent compliance audit."""
    shipment_id: Optional[str] = Field(default=None, description="Consignment or shipment reference ID")
    scenario_title: Optional[str] = Field(default=None, description="Descriptive title of consignment set")
    documents: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dictionary of extracted document data keyed by canonical document type",
    )
    files: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of raw files or binary payload objects",
    )
    generate_pdf: bool = Field(default=True, description="Whether to synthesize a PDF compliance certificate")


class AgentSummary(BaseModel):
    """High-level metrics synthesized by the AI agent."""
    documents_evaluated: int = Field(..., description="Count of trade documents submitted and evaluated")
    missing_documents: List[str] = Field(default_factory=list, description="Omitted canonical document types")
    passed_checks: int = Field(..., description="Number of passed cross-document reconciliation rules")
    failed_checks: int = Field(..., description="Number of failed cross-document reconciliation rules")
    statutory_compliant: bool = Field(..., description="Whether statutory DGFT/CBIC/RBI provisions are met")
    fraud_risk_level: str = Field(..., description="GENUINE, SUSPICIOUS, or HIGH_RISK")
    authenticity_score: float = Field(..., description="Forensic authenticity score (0.0 to 100.0%)")


class AgentAnalysisResponse(BaseModel):
    """Authoritative response payload produced by the LangGraph agent."""
    execution_id: str = Field(..., description="Unique workflow execution ID")
    shipment_id: str = Field(..., description="Shipment identifier")
    scenario_title: Optional[str] = Field(default=None, description="Consignment scenario title")
    overall_compliance_status: str = Field(
        ...,
        description="APPROVED_FOR_EXPORT | CONDITIONAL_REMEDIATION_REQUIRED | REJECTED_CUSTOMS_HOLD",
    )
    compliance_score: float = Field(..., description="Consolidated compliance percentage (0.0 to 100.0%)")
    critical_fraud_flag: bool = Field(..., description="True if any critical forgery/counterfeit signal was detected")
    summary: AgentSummary = Field(..., description="Synthesized multi-dimensional audit metrics")
    reasons: List[str] = Field(default_factory=list, description="Detailed factors determining compliance decision")
    recommendations: List[str] = Field(default_factory=list, description="Actionable remediation steps for customs clearance")
    cross_document_validation: Optional[CrossDocumentValidationResponse] = Field(
        default=None,
        description="Complete 16-rule reconciliation results",
    )
    government_compliance: Optional[GovernmentComplianceReport] = Field(
        default=None,
        description="Indian statutory audit findings",
    )
    fraud_analysis: Optional[FraudAnalysisReport] = Field(
        default=None,
        description="Forensic fraud and tamper detection findings",
    )
    pdf_report_available: bool = Field(default=False, description="True if official PDF audit certificate is ready")
    pdf_report_filename: Optional[str] = Field(default=None, description="Downloadable certificate filename")
    execution_stages: List[str] = Field(
        default_factory=list,
        description="Audit trail of LangGraph stages traversed",
    )
