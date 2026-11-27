"""
Unified Fraud and Tamper Detection Engine.
Orchestrates digital file forensics, tax identifier checksums, mathematical validation,
physical weight laws, and temporal paradox detection into an actionable Authenticity Audit Report.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from server.forensics.identifier_verifier import (
    verify_customs_port,
    verify_gstin,
    verify_iec,
)
from server.forensics.pdf_inspector import inspect_pdf_forensics
from server.forensics.plausibility_checker import (
    verify_mathematical_integrity,
    verify_physical_weight_laws,
)
from server.forensics.temporal_checker import verify_chronological_sequence
from server.schemas.fraud import (
    AnomalySeverity,
    DocumentAnomaly,
    DocumentAuthenticityResult,
    FraudAnalysisReport,
    FraudRiskLevel,
    PdfForensicsResult,
)


def _compute_risk_level(score: float, anomalies: List[DocumentAnomaly]) -> FraudRiskLevel:
    """Calculates risk level tier based on score and severity presence."""
    has_critical = any(a.severity == AnomalySeverity.CRITICAL for a in anomalies)
    if has_critical or score < 60.0:
        return FraudRiskLevel.HIGH_RISK
    if score < 85.0:
        return FraudRiskLevel.SUSPICIOUS
    return FraudRiskLevel.GENUINE


class FraudDetectionEngine:
    """Enterprise forensic engine for detecting counterfeit, tampered, and synthetic trade documents."""

    @classmethod
    def audit_extracted_documents(
        cls,
        documents: Dict[str, Any],
        scenario_title: Optional[str] = None,
    ) -> FraudAnalysisReport:
        """
        Audits extracted document dataset across identifier checksums,
        mathematical extensions, physical weight laws, and temporal sequence.
        """
        audit_id = f"frd_{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        all_anomalies: List[DocumentAnomaly] = []
        doc_breakdowns: List[DocumentAuthenticityResult] = []

        # 1. Commercial Invoice Forensics
        ci = documents.get("Commercial Invoice") or {}
        ci_anomalies: List[DocumentAnomaly] = []
        if ci:
            # Tax ID / GSTIN
            seller = ci.get("exporter_seller") or {}
            gstin = seller.get("tax_id_or_gstin") or ci.get("tax_id_or_gstin") or ""
            iec = seller.get("iec") or ci.get("iec") or ""

            ci_anomalies.extend(verify_gstin(gstin, "Commercial Invoice"))
            ci_anomalies.extend(verify_iec(iec, "Commercial Invoice"))
            ci_anomalies.extend(verify_mathematical_integrity(ci))

            ci_score = 100.0
            for a in ci_anomalies:
                ci_score -= 35.0 if a.severity == AnomalySeverity.CRITICAL else (20.0 if a.severity == AnomalySeverity.HIGH else 10.0)
            ci_score = max(0.0, min(100.0, ci_score))

            doc_breakdowns.append(
                DocumentAuthenticityResult(
                    document_type="Commercial Invoice",
                    authenticity_score=ci_score,
                    risk_level=_compute_risk_level(ci_score, ci_anomalies),
                    anomalies=ci_anomalies,
                )
            )
            all_anomalies.extend(ci_anomalies)

        # 2. Packing List Forensics
        pl = documents.get("Packing List") or {}
        pl_anomalies: List[DocumentAnomaly] = []
        if pl:
            pl_anomalies.extend(verify_physical_weight_laws(pl, "Packing List"))

            pl_score = 100.0
            for a in pl_anomalies:
                pl_score -= 35.0 if a.severity == AnomalySeverity.CRITICAL else 15.0
            pl_score = max(0.0, min(100.0, pl_score))

            doc_breakdowns.append(
                DocumentAuthenticityResult(
                    document_type="Packing List",
                    authenticity_score=pl_score,
                    risk_level=_compute_risk_level(pl_score, pl_anomalies),
                    anomalies=pl_anomalies,
                )
            )
            all_anomalies.extend(pl_anomalies)

        # 3. Shipping Bill Forensics
        sb = documents.get("Shipping Bill") or {}
        sb_anomalies: List[DocumentAnomaly] = []
        if sb:
            port_code = sb.get("customs_port_code") or ""
            sb_iec = sb.get("exporter", {}).get("iec") or sb.get("iec") or ""

            sb_anomalies.extend(verify_customs_port(port_code, "Shipping Bill"))
            sb_anomalies.extend(verify_iec(sb_iec, "Shipping Bill"))
            sb_anomalies.extend(verify_physical_weight_laws(sb, "Shipping Bill"))

            sb_score = 100.0
            for a in sb_anomalies:
                sb_score -= 35.0 if a.severity == AnomalySeverity.CRITICAL else 15.0
            sb_score = max(0.0, min(100.0, sb_score))

            doc_breakdowns.append(
                DocumentAuthenticityResult(
                    document_type="Shipping Bill",
                    authenticity_score=sb_score,
                    risk_level=_compute_risk_level(sb_score, sb_anomalies),
                    anomalies=sb_anomalies,
                )
            )
            all_anomalies.extend(sb_anomalies)

        # 4. Purchase Order & COO (Basic Presence & Weights)
        po = documents.get("Purchase Order") or {}
        if po:
            po_anomalies: List[DocumentAnomaly] = []
            po_score = 100.0
            doc_breakdowns.append(
                DocumentAuthenticityResult(
                    document_type="Purchase Order",
                    authenticity_score=po_score,
                    risk_level=_compute_risk_level(po_score, po_anomalies),
                    anomalies=po_anomalies,
                )
            )

        coo = documents.get("Certificate of Origin") or {}
        if coo:
            coo_anomalies: List[DocumentAnomaly] = []
            coo_score = 100.0
            doc_breakdowns.append(
                DocumentAuthenticityResult(
                    document_type="Certificate of Origin",
                    authenticity_score=coo_score,
                    risk_level=_compute_risk_level(coo_score, coo_anomalies),
                    anomalies=coo_anomalies,
                )
            )

        # 5. Cross-Document Temporal Paradox Analysis
        temporal_anomalies = verify_chronological_sequence(documents)
        all_anomalies.extend(temporal_anomalies)

        # 6. Overall Score Synthesis
        critical_count = sum(1 for a in all_anomalies if a.severity == AnomalySeverity.CRITICAL)
        high_count = sum(1 for a in all_anomalies if a.severity == AnomalySeverity.HIGH)
        medium_count = sum(1 for a in all_anomalies if a.severity == AnomalySeverity.MEDIUM)

        overall_score = 100.0 - (critical_count * 35.0) - (high_count * 20.0) - (medium_count * 10.0)
        overall_score = max(0.0, min(100.0, overall_score))

        overall_risk = _compute_risk_level(overall_score, all_anomalies)

        return FraudAnalysisReport(
            audit_id=audit_id,
            audit_timestamp=timestamp,
            overall_authenticity_score=round(overall_score, 1),
            overall_risk_level=overall_risk,
            total_anomalies=len(all_anomalies),
            critical_anomalies=critical_count,
            anomalies=all_anomalies,
            document_breakdown=doc_breakdowns,
        )

    @classmethod
    def audit_pdf_file(cls, pdf_input: Any, filename: str = "document.pdf") -> PdfForensicsResult:
        """Executes digital file forensics on a PDF file (metadata, producer, fonts)."""
        return inspect_pdf_forensics(pdf_input, filename=filename)
