"""
Task 7: LangGraph AI Customs Compliance Agent Automated Test Suite.

Verifies:
1. Fully compliant shipment (APPROVED_FOR_EXPORT, 100% score).
2. Invoice & PO contract price mismatch (CONDITIONAL_REMEDIATION_REQUIRED).
3. Missing documents handling (Omitted PO & COO tracked, graceful N/A).
4. Invalid GSTIN Checksum Forgery (CRITICAL fraud anomaly, REJECTED_CUSTOMS_HOLD).
5. Manipulated Line-Item Arithmetic (CRITICAL fraud, REJECTED_CUSTOMS_HOLD).
6. Physical Weight Inversion (Net > Gross weight, REJECTED_CUSTOMS_HOLD).
7. Statutory Compliance Failure (Missing IEC/Truthfulness, CONDITIONAL_REMEDIATION_REQUIRED).
8. Critical Fraud Guardrail (Strictly non-overridable hold).
9. PDF Compliance Report generation in agent state (Binary PDF synthesized).
10. Complete End-to-End Workflow Execution Telemetry (All stages traversed).
"""

import sys
import os
from typing import Any, Dict

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from server.controllers.agent_controller import AgentController
from server.schemas.agent import AgentAnalyzeRequest


def get_base_clean_documents() -> Dict[str, Any]:
    """Returns canonical compliant 5-document set with valid Mod-36 GSTIN."""
    valid_gstin = "27AAACG0000A1ZS"  # Mod-36 verified
    return {
        "Commercial Invoice": {
            "invoice_number": "INV-2024-001",
            "buyer_po_number": "PO-998877",
            "invoice_date": "2024-01-15",
            "currency": "EUR",
            "subtotal": 22500.0,
            "total_invoice_amount": 22500.0,
            "total_gross_weight": 1250.0,
            "incoterms": "FOB",
            "exporter_seller": {
                "name": "Global Exports Ltd",
                "tax_id_or_gstin": valid_gstin,
                "iec": "0312345678",
            },
            "consignee_importer": {
                "name": "Acme Trading GmbH",
                "country": "Germany",
            },
            "declaration_and_signatory": {
                "declaration_text": "We declare that this invoice shows actual price and particulars are true.",
            },
            "line_items": [
                {
                    "item_no": 1,
                    "description": "Precision Steel Valves",
                    "hs_code": "8483.40",
                    "quantity": 500,
                    "unit_price": 45.0,
                    "total_amount": 22500.0,
                }
            ],
        },
        "Packing List": {
            "packing_list_number": "PL-2024-001",
            "invoice_reference_number": "INV-2024-001",
            "exporter_seller": {"name": "Global Exports Ltd"},
            "consignee": {"name": "Acme Trading GmbH"},
            "date": "2024-01-15",
            "total_packages_count": 10,
            "total_gross_weight": {"value": 1250.0, "unit": "KG"},
            "total_net_weight": {"value": 1100.0, "unit": "KG"},
            "packages": [
                {
                    "package_no": "1-10",
                    "description": "Precision Steel Valves",
                    "quantity": 500,
                    "unit": "PCS",
                    "net_weight": 1100.0,
                    "gross_weight": 1250.0,
                }
            ],
        },
        "Purchase Order": {
            "po_number": "PO-998877",
            "invoice_number": "INV-2024-001",
            "po_date": "2024-01-10",
            "total_amount": 22500.0,
            "currency": "EUR",
            "incoterms": "FOB",
            "vendor_supplier": {"name": "Global Exports Ltd"},
            "buyer": {"name": "Acme Trading GmbH"},
            "line_items": [
                {
                    "item_no": 1,
                    "description": "Precision Steel Valves",
                    "quantity": 500,
                    "unit_price": 45.0,
                    "total_price": 22500.0,
                }
            ],
        },
        "Shipping Bill": {
            "shipping_bill_number": "SB-11223344",
            "invoice_number": "INV-2024-001",
            "shipping_bill_date": "2024-01-16",
            "customs_port_code": "INMAA1",
            "currency": "EUR",
            "total_invoice_value": 22500.0,
            "fob_value": 22500.0,
            "gross_weight": {"value": 1250.0, "unit": "KG"},
            "net_weight": {"value": 1100.0, "unit": "KG"},
            "exporter": {"name": "Global Exports Ltd", "iec": "0312345678"},
            "consignee": {"name": "Acme Trading GmbH"},
            "items": [
                {
                    "item_no": 1,
                    "ritc_hs_code": "84834000",
                    "quantity": 500,
                    "unit": "PCS",
                    "fob_value": 22500.0,
                }
            ],
        },
        "Certificate of Origin": {
            "certificate_number": "COO-556677",
            "issuing_authority_or_chamber": "Bombay Chamber of Commerce",
            "certificate_date": "2024-01-16",
            "origin_criterion": "Wholly Obtained (WO)",
            "exporter": {"name": "Global Exports Ltd"},
            "importer_or_consignee": {"name": "Acme Trading GmbH"},
            "item_details": [
                {
                    "item_no": 1,
                    "hs_code": "8483.40",
                    "invoice_number": "INV-2024-001",
                    "quantity_or_weight": "500 PCS",
                }
            ],
        },
    }


def test_scenario_1_fully_compliant():
    print("[1/10] Testing Scenario 1: Fully Compliant Consignment...")
    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-001",
        scenario_title="Clean Industrial Machinery to Germany",
        documents=get_base_clean_documents(),
        generate_pdf=True,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "APPROVED_FOR_EXPORT"
    assert res.compliance_score >= 90.0
    assert not res.critical_fraud_flag
    assert res.summary.failed_checks == 0
    assert res.summary.statutory_compliant
    assert res.summary.fraud_risk_level == "GENUINE"
    assert res.pdf_report_available
    print(f"       Passed! Status: {res.overall_compliance_status}, Score: {res.compliance_score}%.")


def test_scenario_2_price_currency_mismatch():
    print("[2/10] Testing Scenario 2: Invoice & PO Price Mismatch...")
    docs = get_base_clean_documents()
    # Contract mismatch: PO amount is 20,000 EUR (Invoice exceeds authorized limit) and Currency USD
    docs["Purchase Order"]["total_amount"] = 20000.0
    docs["Purchase Order"]["currency"] = "USD"

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-002",
        scenario_title="Price Mismatch Consignment",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "CONDITIONAL_REMEDIATION_REQUIRED"
    assert res.summary.failed_checks >= 1
    assert any("XDOC_FIN_008" in r or "XDOC_CURR_004" in r or "Discrepancy" in r for r in res.reasons)
    assert not res.critical_fraud_flag
    print(f"       Passed! Correctly assigned status '{res.overall_compliance_status}' with {res.summary.failed_checks} failed checks.")


def test_scenario_3_missing_documents():
    print("[3/10] Testing Scenario 3: Missing Documents (Omitted PO and COO)...")
    docs = get_base_clean_documents()
    del docs["Purchase Order"]
    del docs["Certificate of Origin"]

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-003",
        scenario_title="Partial Document Submission",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert "Purchase Order" in res.summary.missing_documents
    assert "Certificate of Origin" in res.summary.missing_documents
    assert len(res.summary.missing_documents) == 2
    assert res.summary.documents_evaluated == 3
    print(f"       Passed! Detected missing documents: {res.summary.missing_documents}.")


def test_scenario_4_invalid_gstin_forgery():
    print("[4/10] Testing Scenario 4: Invalid GSTIN Checksum Forgery...")
    docs = get_base_clean_documents()
    # Tamper GSTIN checksum character from 'S' to bogus '9'
    docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = "27AAACG0000A1Z9"

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-004",
        scenario_title="Fabricated GSTIN Consignment",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "REJECTED_CUSTOMS_HOLD"
    assert res.critical_fraud_flag
    assert any("FRD_GSTIN_CHKSUM_005B" in r for r in res.reasons)
    print(f"       Passed! Forced status '{res.overall_compliance_status}' on GSTIN forgery.")


def test_scenario_5_manipulated_line_items_math():
    print("[5/10] Testing Scenario 5: Manipulated Line Item Arithmetic...")
    docs = get_base_clean_documents()
    # Tampered line item total: 500 * 45 = 22,500, but forged as 35,000
    docs["Commercial Invoice"]["line_items"][0]["total_amount"] = 35000.0

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-005",
        scenario_title="Math Manipulated Invoice",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "REJECTED_CUSTOMS_HOLD"
    assert res.critical_fraud_flag
    assert any("FRD_LINE_MATH" in r for r in res.reasons)
    print(f"       Passed! Forced status '{res.overall_compliance_status}' on arithmetic tampering.")


def test_scenario_6_physical_weight_inversion():
    print("[6/10] Testing Scenario 6: Physical Weight Inversion (Net > Gross Weight)...")
    docs = get_base_clean_documents()
    # Net Weight 1600 kg exceeds Gross Weight 1250 kg
    docs["Packing List"]["total_net_weight"]["value"] = 1600.0

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-006",
        scenario_title="Physical Weight Inversion",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "REJECTED_CUSTOMS_HOLD"
    assert res.critical_fraud_flag
    assert any("FRD_WEIGHT_INVERT_009" in r for r in res.reasons)
    print(f"       Passed! Forced status '{res.overall_compliance_status}' on physical weight law inversion.")


def test_scenario_7_statutory_compliance_failure():
    print("[7/10] Testing Scenario 7: Statutory Non-Compliance (Missing IEC)...")
    docs = get_base_clean_documents()
    docs["Commercial Invoice"]["exporter_seller"]["iec"] = ""
    docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = ""

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-007",
        scenario_title="Missing IEC Consignment",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "CONDITIONAL_REMEDIATION_REQUIRED"
    assert not res.summary.statutory_compliant
    assert any("DGFT_FTP2023_P2_05" in r for r in res.reasons)
    print(f"       Passed! Correctly flagged statutory non-compliance: {res.overall_compliance_status}.")


def test_scenario_8_critical_fraud_guardrail_non_overridable():
    print("[8/10] Testing Scenario 8: Non-Overridable Critical Fraud Guardrail...")
    # Even when all 16 cross-document rules and statutory provisions are valid,
    # a critical fraud indicator MUST NOT be overridden by a PASS decision.
    docs = get_base_clean_documents()
    docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = "27AAACG0000A1Z9"

    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-008",
        scenario_title="Guardrail Verification",
        documents=docs,
    )
    res = AgentController.analyze_shipment(req)

    assert res.overall_compliance_status == "REJECTED_CUSTOMS_HOLD", "Critical fraud MUST reject the consignment!"
    assert res.compliance_score <= 40.0
    print("       Passed! Fraud guardrail strictly prevents false PASS decisions.")


def test_scenario_9_pdf_report_synthesis():
    print("[9/10] Testing Scenario 9: PDF Compliance Certificate Synthesis in State...")
    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-009",
        scenario_title="PDF Synthesis Test",
        documents=get_base_clean_documents(),
        generate_pdf=True,
    )
    res = AgentController.analyze_shipment(req)

    assert res.pdf_report_available
    assert res.pdf_report_filename is not None
    assert res.pdf_report_filename.endswith(".pdf")
    print(f"       Passed! Generated certificate: {res.pdf_report_filename}.")


def test_scenario_10_end_to_end_telemetry():
    print("[10/10] Testing Scenario 10: End-to-End Workflow Execution Telemetry...")
    req = AgentAnalyzeRequest(
        shipment_id="SHP-EXP-010",
        scenario_title="Full Audit Telemetry",
        documents=get_base_clean_documents(),
        generate_pdf=True,
    )
    res = AgentController.analyze_shipment(req)

    expected_stages = [
        "DOCUMENT_INPUT",
        "COMPLETENESS_CHECK",
        "CROSS_DOCUMENT_VALIDATION",
        "STATUTORY_VERIFICATION",
        "FAKE_DOCUMENT_DETECTION",
        "COMPLIANCE_DECISION",
        "PDF_REPORT_GENERATION",
        "COMPLETED",
    ]
    for stage in expected_stages:
        assert stage in res.execution_stages, f"Expected stage '{stage}' in execution telemetry"

    assert len(res.recommendations) > 0
    assert res.execution_id.startswith("agt_")
    print(f"       Passed! Traversed {len(res.execution_stages)} stages: {res.execution_stages}.")


def main():
    print("======================================================================")
    print("TASK 7: LANGGRAPH AI AGENT 10-SCENARIO AUTOMATED TEST SUITE")
    print("======================================================================")
    test_scenario_1_fully_compliant()
    test_scenario_2_price_currency_mismatch()
    test_scenario_3_missing_documents()
    test_scenario_4_invalid_gstin_forgery()
    test_scenario_5_manipulated_line_items_math()
    test_scenario_6_physical_weight_inversion()
    test_scenario_7_statutory_compliance_failure()
    test_scenario_8_critical_fraud_guardrail_non_overridable()
    test_scenario_9_pdf_report_synthesis()
    test_scenario_10_end_to_end_telemetry()
    print("======================================================================")
    print("ALL 10 LANGGRAPH AGENT SCENARIOS PASSED SUCCESSFULLY!")
    print("======================================================================")


if __name__ == "__main__":
    main()
