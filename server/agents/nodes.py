"""
LangGraph Nodes for Export Customs Compliance AI Agent.
Encapsulates all 10 specialized workflow steps, strictly reusing existing domain modules.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from server.agents.state import CustomsComplianceAgentState
from server.compliance.engine import validate_documents
from server.forensics.engine import FraudDetectionEngine
from server.reports.pdf_generator import generate_compliance_pdf_report
from server.rules.checker import verify_government_rules
from server.schemas.fraud import FraudRiskLevel
from server.schemas.report import GeneratePdfReportRequest, ShipmentDetails

CANONICAL_TRADE_DOCUMENTS = [
    "Commercial Invoice",
    "Packing List",
    "Purchase Order",
    "Shipping Bill",
    "Certificate of Origin",
]


def document_input_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 1: Normalizes input payload and initializes execution tracking."""
    exec_id = state.get("execution_id") or f"agt_{uuid.uuid4().hex[:10]}"
    history = list(state.get("execution_history") or [])
    history.append("DOCUMENT_INPUT")

    uploaded = state.get("uploaded_files") or []
    extracted = state.get("extracted_documents") or {}

    input_type = "RAW_FILES" if uploaded else "STRUCTURED_DATA"

    return {
        **state,
        "execution_id": exec_id,
        "input_type": input_type,
        "execution_history": history,
        "workflow_stage": "DOCUMENT_INPUT",
    }


def document_classification_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 2: Classifies uploaded documents into the 5 standard trade types."""
    history = list(state.get("execution_history") or [])
    history.append("DOCUMENT_CLASSIFICATION")

    classified = dict(state.get("classified_documents") or {})
    extracted = dict(state.get("extracted_documents") or {})

    # If documents were already provided pre-classified in extracted_documents, preserve them
    for doc_name in extracted.keys():
        classified[doc_name] = doc_name

    # If raw files exist, run heuristic classifier
    uploaded = state.get("uploaded_files") or []
    if uploaded:
        from server.document_intelligence.classifier import classify_document_type
        for item in uploaded:
            fname = item.get("filename", "")
            text = item.get("text", "")
            if fname and text:
                classification = classify_document_type(text=text, original_filename=fname)
                classified[fname] = classification.value

    return {
        **state,
        "classified_documents": classified,
        "execution_history": history,
        "workflow_stage": "DOCUMENT_CLASSIFICATION",
    }


def ocr_data_extraction_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 3: Coordinates OCR and structured data extraction for raw files."""
    history = list(state.get("execution_history") or [])
    history.append("OCR_DATA_EXTRACTION")

    extracted = dict(state.get("extracted_documents") or {})
    errors = list(state.get("ocr_extraction_errors") or [])

    # If raw files are provided and not yet extracted
    uploaded = state.get("uploaded_files") or []
    classified = state.get("classified_documents") or {}

    for item in uploaded:
        fname = item.get("filename", "")
        doc_type = classified.get(fname)
        if doc_type and doc_type not in extracted:
            # Check for pre-parsed data in item or local disk fallback
            if "data" in item:
                extracted[doc_type] = item["data"]
            elif "text" in item:
                from server.document_intelligence.extractor import extract_document_data
                try:
                    data = extract_document_data(doc_type, item["text"], source_filename=fname, save_to_disk=False)
                    extracted[doc_type] = data
                except Exception as exc:
                    errors.append(f"Failed extraction for {doc_type} ({fname}): {str(exc)}")

    return {
        **state,
        "extracted_documents": extracted,
        "ocr_extraction_errors": errors,
        "execution_history": history,
        "workflow_stage": "OCR_DATA_EXTRACTION",
    }


def completeness_check_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 4: Evaluates presence of the 5 canonical documents."""
    history = list(state.get("execution_history") or [])
    history.append("COMPLETENESS_CHECK")

    extracted = state.get("extracted_documents") or {}
    present = set(extracted.keys())
    missing = [d for d in CANONICAL_TRADE_DOCUMENTS if d not in present]

    return {
        **state,
        "missing_documents": missing,
        "execution_history": history,
        "workflow_stage": "COMPLETENESS_CHECK",
    }


def cross_document_validation_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 5: Executes the 16 cross-document reconciliation rules."""
    history = list(state.get("execution_history") or [])
    history.append("CROSS_DOCUMENT_VALIDATION")

    extracted = state.get("extracted_documents") or {}
    validation_res = validate_documents(extracted)

    return {
        **state,
        "cross_document_results": validation_res,
        "execution_history": history,
        "workflow_stage": "CROSS_DOCUMENT_VALIDATION",
    }


def statutory_verification_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 6: Audits shipment documents against DGFT, CBIC, and RBI mandates."""
    history = list(state.get("execution_history") or [])
    history.append("STATUTORY_VERIFICATION")

    extracted = state.get("extracted_documents") or {}
    statutory_res = verify_government_rules(extracted)

    return {
        **state,
        "statutory_results": statutory_res,
        "execution_history": history,
        "workflow_stage": "STATUTORY_VERIFICATION",
    }


def fake_document_detection_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 7: Executes multi-layer forensic analysis (GSTIN, Math, Weight laws, Chronology)."""
    history = list(state.get("execution_history") or [])
    history.append("FAKE_DOCUMENT_DETECTION")

    extracted = state.get("extracted_documents") or {}
    fraud_res = FraudDetectionEngine.audit_extracted_documents(
        documents=extracted,
        scenario_title=state.get("scenario_title"),
    )

    return {
        **state,
        "fraud_results": fraud_res,
        "execution_history": history,
        "workflow_stage": "FAKE_DOCUMENT_DETECTION",
    }


def compliance_decision_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """
    Node 8: Synthesizes validation, statutory, and forensic telemetry into an authoritative decision.
    Strictly enforces non-overridable hold on critical fraud indicators.
    """
    history = list(state.get("execution_history") or [])
    history.append("COMPLIANCE_DECISION")

    val = state.get("cross_document_results")
    gov = state.get("statutory_results")
    fraud = state.get("fraud_results")
    missing = state.get("missing_documents") or []

    reasons: List[str] = []
    recommendations: List[str] = []

    # 1. Critical Fraud Guardrail
    critical_fraud = False
    if fraud:
        if fraud.critical_anomalies > 0 or fraud.overall_risk_level == FraudRiskLevel.HIGH_RISK:
            critical_fraud = True
            for anomaly in fraud.anomalies:
                if anomaly.severity.value in ("CRITICAL", "HIGH"):
                    reasons.append(f"Forensic Anomaly [{anomaly.anomaly_id}]: {anomaly.rule_name} - {anomaly.evidence}")
                    if anomaly.remediation:
                        recommendations.append(anomaly.remediation)

    # 2. Missing Documents Analysis
    if missing:
        reasons.append(f"Missing canonical trade documents: {', '.join(missing)}.")
        recommendations.append(f"Upload remaining documents ({', '.join(missing)}) for a complete 5-document customs audit.")

    # 3. Cross-Document Discrepancies
    val_failed = False
    if val:
        failures = [c for c in val.cross_document_results if c.status.value == "FAIL"]
        if failures:
            val_failed = True
            for f in failures:
                reasons.append(f"Discrepancy [{f.check_id}]: {f.rule_name} - {f.discrepancy or f.message}")
                remed = f"Reconcile {f.field_name} across {', '.join(f.documents_involved)} before ICEGATE filing."
                if remed not in recommendations:
                    recommendations.append(remed)

    # 4. Statutory Non-Compliance
    gov_non_compliant = False
    if gov:
        stat_violations = [f for f in gov.findings if f.status.value == "NON_COMPLIANT"]
        if stat_violations:
            gov_non_compliant = True
            for v in stat_violations:
                reasons.append(f"Statutory Violation [{v.rule_id}]: {v.rule_title} under {v.policy_document} ({v.para_ref}).")
                if v.action_required:
                    recommendations.append(v.action_required)

    # 5. Authoritative Decision & Score Synthesis
    if critical_fraud:
        decision = "REJECTED_CUSTOMS_HOLD"
        score = min(fraud.overall_authenticity_score if fraud else 30.0, 40.0)
    elif val_failed or gov_non_compliant:
        decision = "CONDITIONAL_REMEDIATION_REQUIRED"
        applicable = (val.summary.total_checks - val.summary.not_applicable) if val and val.summary else 16
        val_score = round((val.summary.passed / applicable) * 100, 1) if applicable > 0 else 70.0
        score = min(val_score, 85.0)
    elif missing and ("Commercial Invoice" in missing or "Shipping Bill" in missing):
        decision = "CONDITIONAL_REMEDIATION_REQUIRED"
        score = 65.0
    else:
        decision = "APPROVED_FOR_EXPORT"
        score = 100.0 if not missing else 90.0
        reasons.append("All applicable cross-document rules and statutory provisions verified. Document set authentic.")
        recommendations.append("Consignment documentation is approved for Let Export Order (LEO) customs clearance.")

    return {
        **state,
        "overall_compliance_status": decision,
        "compliance_score": round(score, 1),
        "reasons": reasons,
        "recommendations": recommendations,
        "critical_fraud_flag": critical_fraud,
        "execution_history": history,
        "workflow_stage": "COMPLIANCE_DECISION",
    }


def pdf_report_generation_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 9: Renders official A4 PDF Compliance Certificate from state telemetry."""
    history = list(state.get("execution_history") or [])
    history.append("PDF_REPORT_GENERATION")

    if not state.get("generate_pdf", True):
        return {
            **state,
            "execution_history": history,
            "workflow_stage": "PDF_REPORT_GENERATION",
        }

    val = state.get("cross_document_results")
    gov = state.get("statutory_results")
    extracted = state.get("extracted_documents") or {}
    ci = extracted.get("Commercial Invoice") or {}
    sb = extracted.get("Shipping Bill") or {}

    shipment = ShipmentDetails(
        exporter_name=(
            (ci.get("exporter_seller") or {}).get("name")
            or (sb.get("exporter") or {}).get("name")
        ),
        exporter_iec=(
            (ci.get("exporter_seller") or {}).get("iec")
            or sb.get("iec")
            or (sb.get("exporter") or {}).get("iec")
        ),
        exporter_gstin=(
            (ci.get("exporter_seller") or {}).get("tax_id_or_gstin")
            or sb.get("gstin")
        ),
        consignee_name=(
            (ci.get("consignee_importer") or {}).get("name")
            or (sb.get("consignee") or {}).get("name")
        ),
        destination_country=(
            (ci.get("consignee_importer") or {}).get("country")
            or sb.get("country_of_destination")
        ),
        invoice_number=ci.get("invoice_number") or sb.get("invoice_number"),
        declared_currency=ci.get("currency") or sb.get("currency"),
        total_declared_value=(
            ci.get("total_invoice_amount")
            or ci.get("subtotal")
            or sb.get("fob_value")
            or sb.get("total_invoice_value")
        ),
        incoterms=ci.get("incoterms"),
    )

    pdf_bytes = None
    pdf_filename = None
    if val:
        req = GeneratePdfReportRequest(
            shipment_details=shipment,
            cross_document_validation=val,
            government_compliance=gov,
            scenario_title=state.get("scenario_title") or "Export Customs Compliance Audit",
        )
        pdf_bytes = generate_compliance_pdf_report(req)
        pdf_filename = f"Compliance_Certificate_{val.audit_id}.pdf"

    return {
        **state,
        "pdf_report_bytes": pdf_bytes,
        "pdf_report_filename": pdf_filename,
        "execution_history": history,
        "workflow_stage": "PDF_REPORT_GENERATION",
    }


def final_response_node(state: CustomsComplianceAgentState) -> CustomsComplianceAgentState:
    """Node 10: Finalizes workflow execution and serializes output telemetry."""
    history = list(state.get("execution_history") or [])
    history.append("COMPLETED")

    return {
        **state,
        "workflow_stage": "COMPLETED",
        "execution_history": history,
    }
