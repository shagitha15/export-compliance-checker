"""
Pydantic Schemas for Task 5 PDF Compliance Report Generation.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from server.schemas.compliance import GovernmentComplianceReport
from server.schemas.validation import CrossDocumentValidationResponse


class ShipmentDetails(BaseModel):
    """Optional metadata detailing the shipment parties and commercial invoice metrics."""
    exporter_name: Optional[str] = Field(default=None, description="Legal name of the exporting entity")
    exporter_iec: Optional[str] = Field(default=None, description="10-digit DGFT Importer Exporter Code")
    exporter_gstin: Optional[str] = Field(default=None, description="GSTIN or Tax identification number")
    consignee_name: Optional[str] = Field(default=None, description="Legal name of the foreign consignee / buyer")
    destination_country: Optional[str] = Field(default=None, description="Country of destination")
    invoice_number: Optional[str] = Field(default=None, description="Primary commercial invoice number")
    declared_currency: Optional[str] = Field(default=None, description="Invoice billing currency (e.g. USD, EUR)")
    total_declared_value: Optional[float] = Field(default=None, description="Total declared commercial invoice amount")
    incoterms: Optional[str] = Field(default=None, description="Incoterms 2020 delivery terms (e.g. FOB, CIF)")


class GeneratePdfReportRequest(BaseModel):
    """Payload for generating an official export customs documentation compliance PDF certificate."""
    batch_id: Optional[str] = Field(
        default=None,
        description="Batch identifier when generating a report for a batch upload",
    )
    batch_status: Optional[str] = Field(
        default=None,
        description="Overall batch ingestion status (SUCCESS, PARTIAL_SUCCESS, FAILED)",
    )
    report_generated_at: Optional[str] = Field(
        default=None,
        description="Optional ISO 8601 timestamp for report generation",
    )
    shipment_details: Optional[ShipmentDetails] = Field(
        default=None,
        description="Shipment metadata (exporter, consignee, valuation). If omitted, inferred from extracted documents.",
    )
    uploaded_documents: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="List of uploaded document metadata (filename, document_type, status, size, error)",
    )
    extracted_documents: Optional[dict[str, dict[str, Any]]] = Field(
        default=None,
        description="Map of canonical document type to extracted JSON payload",
    )
    extracted_trade_info: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional pre-summarized extracted trade fields",
    )
    cross_document_validation: Optional[CrossDocumentValidationResponse] = Field(
        default=None,
        description="Two-stage cross-document reconciliation results evaluated across trade documents",
    )
    government_compliance: Optional[GovernmentComplianceReport] = Field(
        default=None,
        description="Statutory audit against official Indian export regulations (DGFT, CBIC, RBI)",
    )
    fraud_analysis: Optional[dict[str, Any]] = Field(
        default=None,
        description="Fake document & forensic authenticity audit results",
    )
    recommendations: Optional[list[str]] = Field(
        default=None,
        description="Optional explicit remediation recommendations",
    )
    scenario_title: Optional[str] = Field(
        default=None,
        description="Descriptive title of the audited consignment scenario",
    )
