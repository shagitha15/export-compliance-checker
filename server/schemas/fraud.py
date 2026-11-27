"""
Pydantic Schemas for Task 6 Fake Document and Tamper Detection Engine.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FraudRiskLevel(str, Enum):
    """Categorical risk tier for document authenticity."""
    GENUINE = "GENUINE"              # Authenticity Score >= 85%, no critical anomalies
    SUSPICIOUS = "SUSPICIOUS"        # Authenticity Score 60% - 84%, or advisory anomalies
    HIGH_RISK = "HIGH_RISK"          # Authenticity Score < 60%, or critical forgery indicators


class AnomalyCategory(str, Enum):
    """Classification taxonomy for forensic anomalies."""
    METADATA_TAMPERING = "METADATA_TAMPERING"
    TYPOGRAPHY_ANOMALY = "TYPOGRAPHY_ANOMALY"
    IDENTIFIER_FRAUD = "IDENTIFIER_FRAUD"
    NUMERICAL_FORGERY = "NUMERICAL_FORGERY"
    PHYSICAL_ANOMALY = "PHYSICAL_ANOMALY"
    TEMPORAL_PARADOX = "TEMPORAL_PARADOX"


class AnomalySeverity(str, Enum):
    """Severity ranking of detected forensic anomaly."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DocumentAnomaly(BaseModel):
    """Individual forensic anomaly or forgery indicator."""
    anomaly_id: str = Field(..., description="Unique anomaly identifier code, e.g. FRD_GSTIN_CHKSUM_005")
    category: AnomalyCategory = Field(..., description="Forensic anomaly classification")
    severity: AnomalySeverity = Field(..., description="Severity weight: CRITICAL, HIGH, MEDIUM, LOW")
    rule_name: str = Field(..., description="Short title of the violated integrity rule")
    description: str = Field(..., description="Detailed explanation of the forensic rule")
    evidence: str = Field(..., description="Observed evidence or mismatch detected in the document")
    remediation: Optional[str] = Field(default=None, description="Recommended remediation or investigation action")
    document_type: Optional[str] = Field(default=None, description="Document type involved")
    field_name: Optional[str] = Field(default=None, description="Name of the affected field")


class DocumentAuthenticityResult(BaseModel):
    """Forensic evaluation for a single trade document."""
    document_type: str = Field(..., description="One of the canonical customs trade document types")
    filename: Optional[str] = Field(default=None, description="Source PDF filename if available")
    authenticity_score: float = Field(..., description="Calculated authenticity score (0.0 to 100.0%)")
    risk_level: FraudRiskLevel = Field(..., description="GENUINE, SUSPICIOUS, or HIGH_RISK")
    anomalies: List[DocumentAnomaly] = Field(default_factory=list, description="Anomalies detected in this document")


class FraudAnalysisReport(BaseModel):
    """Consolidated fraud and authenticity audit report for a shipment package."""
    audit_id: str = Field(..., description="Unique forensic audit identifier")
    audit_timestamp: str = Field(..., description="ISO 8601 audit timestamp")
    overall_authenticity_score: float = Field(..., description="Aggregated authenticity percentage (0.0 to 100.0%)")
    overall_risk_level: FraudRiskLevel = Field(..., description="Consolidated risk tier")
    total_anomalies: int = Field(..., description="Total count of anomalies detected")
    critical_anomalies: int = Field(..., description="Count of critical severity anomalies")
    anomalies: List[DocumentAnomaly] = Field(default_factory=list, description="Flat list of all detected anomalies")
    document_breakdown: List[DocumentAuthenticityResult] = Field(
        default_factory=list,
        description="Per-document forensic authenticity results",
    )


class InspectDocumentsRequest(BaseModel):
    """Payload to evaluate extracted document dataset for fraud and forgery signals."""
    documents: Dict[str, Any] = Field(..., description="Dictionary of extracted document data keyed by document type")
    scenario_title: Optional[str] = Field(default=None, description="Optional title or shipment reference")


class PdfForensicsResult(BaseModel):
    """Digital forensics report extracted from binary PDF file inspection."""
    filename: str = Field(..., description="Name of the evaluated PDF file")
    page_count: int = Field(..., description="Total page count")
    producer: Optional[str] = Field(default=None, description="PDF producer software")
    creator: Optional[str] = Field(default=None, description="PDF creator tool")
    creation_date: Optional[str] = Field(default=None, description="Creation timestamp from metadata")
    mod_date: Optional[str] = Field(default=None, description="Modification timestamp from metadata")
    fonts_detected: List[str] = Field(default_factory=list, description="Unique font family names detected")
    is_tampered: bool = Field(default=False, description="Whether digital tampering was flagged")
    anomalies: List[DocumentAnomaly] = Field(default_factory=list, description="Detected digital anomalies")
