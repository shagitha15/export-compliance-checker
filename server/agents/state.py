"""
State Definition for LangGraph Customs Compliance AI Agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from server.schemas.compliance import GovernmentComplianceReport
from server.schemas.fraud import FraudAnalysisReport
from server.schemas.validation import CrossDocumentValidationResponse


class CustomsComplianceAgentState(TypedDict, total=False):
    """
    Shared state for the 10-node LangGraph export customs compliance workflow.
    Tracks document ingestion, extraction, cross-document reconciliation,
    statutory checks, fraud forensics, final decision synthesis, and PDF artifacts.
    """
    # 1. Consignment Identification
    execution_id: str
    shipment_id: str
    scenario_title: Optional[str]
    input_type: str                            # "RAW_FILES" or "STRUCTURED_DATA"

    # 2. Ingestion & Extraction Telemetry
    uploaded_files: List[Dict[str, Any]]       # Metadata, raw streams or filenames
    classified_documents: Dict[str, str]       # filename -> DocumentType
    extracted_documents: Dict[str, Any]        # DocumentType -> parsed JSON
    missing_documents: List[str]               # List of omitted standard documents
    ocr_extraction_errors: List[str]           # Any OCR or parsing errors encountered

    # 3. Domain Engine Audit Results
    cross_document_results: Optional[CrossDocumentValidationResponse]
    statutory_results: Optional[GovernmentComplianceReport]
    fraud_results: Optional[FraudAnalysisReport]

    # 4. Synthesized Compliance Decision
    overall_compliance_status: str             # "APPROVED_FOR_EXPORT" | "CONDITIONAL_REMEDIATION_REQUIRED" | "REJECTED_CUSTOMS_HOLD"
    compliance_score: float                    # Consolidated compliance score (0.0 to 100.0%)
    reasons: List[str]                         # Core findings leading to decision
    recommendations: List[str]                 # Actionable remediation instructions
    critical_fraud_flag: bool                  # Enforces non-overridable rejection hold

    # 5. Output Artifacts
    pdf_report_bytes: Optional[bytes]
    pdf_report_filename: Optional[str]
    generate_pdf: bool                         # Whether to generate PDF in node 9

    # 6. Workflow Lifecycle Telemetry
    workflow_stage: str
    execution_history: List[str]
    error: Optional[str]
