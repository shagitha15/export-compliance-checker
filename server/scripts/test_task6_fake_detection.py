"""
Task 6: Fake Document & Tamper Detection Automated Verification Suite.

Tests:
1. Clean Authentic Shipment (100% Authenticity, GENUINE).
2. Fabricated GSTIN Checksum Forgery (CRITICAL, HIGH_RISK).
3. Line Item Arithmetic & Valuation Manipulation (CRITICAL, HIGH_RISK).
4. Physical Law Inversion: Net Weight > Gross Weight (CRITICAL, HIGH_RISK).
5. Temporal Chronology Paradox (HIGH, SUSPICIOUS/HIGH_RISK).
6. Digital PDF File & Metadata Inspection.
7. FraudController & InspectDocumentsRequest serialization.
"""

import sys
import os
from pathlib import Path
from typing import Any, Dict

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import fitz  # PyMuPDF
from server.controllers.fraud_controller import FraudController
from server.forensics.engine import FraudDetectionEngine
from server.forensics.identifier_verifier import calculate_gstin_checksum, verify_gstin
from server.forensics.pdf_inspector import inspect_pdf_forensics
from server.schemas.fraud import (
    AnomalyCategory,
    AnomalySeverity,
    FraudRiskLevel,
    InspectDocumentsRequest,
)


def get_base_clean_documents() -> Dict[str, Any]:
    """Returns canonical compliant 5-document set with valid Mod-36 GSTIN."""
    valid_gstin = "27AAACG0000A1ZS"  # Mod-36 verified
    return {
        "Commercial Invoice": {
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "currency": "EUR",
            "subtotal": 22500.0,
            "total_invoice_amount": 22500.0,
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
            "line_items": [
                {
                    "item_no": 1,
                    "description": "Precision Steel Valves",
                    "quantity": 500,
                    "unit_price": 45.0,
                    "total_amount": 22500.0,
                }
            ],
        },
        "Packing List": {
            "packing_list_number": "PL-2024-001",
            "date": "2024-01-15",
            "total_packages_count": 10,
            "total_gross_weight": {"value": 1250.0, "unit": "KG"},
            "total_net_weight": {"value": 1100.0, "unit": "KG"},
        },
        "Purchase Order": {
            "po_number": "PO-998877",
            "po_date": "2024-01-10",  # Prior to invoice
            "total_amount": 22500.0,
            "currency": "EUR",
        },
        "Shipping Bill": {
            "shipping_bill_number": "SB-11223344",
            "shipping_bill_date": "2024-01-16",  # After invoice
            "customs_port_code": "INMAA1",
            "gross_weight": 1250.0,
            "net_weight": 1100.0,
        },
        "Certificate of Origin": {
            "certificate_number": "COO-556677",
            "certificate_date": "2024-01-16",  # Concurrent/after invoice
            "exporter": {"name": "Global Exports Ltd"},
        },
    }


def test_clean_authentic_shipment():
    print("[1/7] Testing Clean Authentic Consignment (Expect 100% Authenticity, GENUINE)...")
    docs = get_base_clean_documents()
    report = FraudDetectionEngine.audit_extracted_documents(docs)

    assert report.overall_authenticity_score == 100.0, f"Expected 100.0%, got {report.overall_authenticity_score}%"
    assert report.overall_risk_level == FraudRiskLevel.GENUINE, f"Expected GENUINE, got {report.overall_risk_level}"
    assert report.total_anomalies == 0, f"Expected 0 anomalies, got {report.total_anomalies}"
    assert report.critical_anomalies == 0
    print(f"      Passed! Score: {report.overall_authenticity_score}%, Risk: {report.overall_risk_level.value}.")


def test_fabricated_gstin_checksum_forgery():
    print("[2/7] Testing Fabricated GSTIN Checksum Forgery (Expect CRITICAL Anomaly, HIGH_RISK)...")
    docs = get_base_clean_documents()
    # Replace valid 15th checksum character 'S' with bogus check digit '9'
    docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = "27AAACG0000A1Z9"

    report = FraudDetectionEngine.audit_extracted_documents(docs)

    assert report.overall_risk_level == FraudRiskLevel.HIGH_RISK
    assert report.critical_anomalies >= 1
    checksum_anomalies = [a for a in report.anomalies if a.anomaly_id == "FRD_GSTIN_CHKSUM_005B"]
    assert len(checksum_anomalies) == 1, "Expected GSTIN Mod-36 checksum anomaly"
    assert checksum_anomalies[0].severity == AnomalySeverity.CRITICAL
    print(f"      Passed! Flagged {checksum_anomalies[0].anomaly_id}: {checksum_anomalies[0].rule_name}.")


def test_line_item_math_manipulation():
    print("[3/7] Testing Line Item Arithmetic Manipulation (Expect CRITICAL Anomaly, HIGH_RISK)...")
    docs = get_base_clean_documents()
    # Tamper line item extension: 500 * 45 = 22,500, but forged as 35,000
    docs["Commercial Invoice"]["line_items"][0]["total_amount"] = 35000.0

    report = FraudDetectionEngine.audit_extracted_documents(docs)

    assert report.overall_risk_level == FraudRiskLevel.HIGH_RISK
    math_anomalies = [a for a in report.anomalies if "FRD_LINE_MATH" in a.anomaly_id or "FRD_SUBTOTAL" in a.anomaly_id]
    assert len(math_anomalies) >= 1, "Expected mathematical calculation anomaly"
    assert math_anomalies[0].severity == AnomalySeverity.CRITICAL
    print(f"      Passed! Flagged {math_anomalies[0].anomaly_id}: {math_anomalies[0].evidence}.")


def test_physical_weight_inversion():
    print("[4/7] Testing Physical Weight Inversion (Net Weight > Gross Weight) (Expect CRITICAL, HIGH_RISK)...")
    docs = get_base_clean_documents()
    # Physical impossibility: Net Weight 1600 kg > Gross Weight 1250 kg
    docs["Packing List"]["total_net_weight"]["value"] = 1600.0

    report = FraudDetectionEngine.audit_extracted_documents(docs)

    assert report.overall_risk_level == FraudRiskLevel.HIGH_RISK
    weight_anomalies = [a for a in report.anomalies if a.anomaly_id == "FRD_WEIGHT_INVERT_009"]
    assert len(weight_anomalies) == 1, "Expected Net > Gross weight physical law violation anomaly"
    assert weight_anomalies[0].severity == AnomalySeverity.CRITICAL
    print(f"      Passed! Flagged {weight_anomalies[0].anomaly_id}: {weight_anomalies[0].evidence}.")


def test_temporal_chronology_paradox():
    print("[5/7] Testing Temporal Chronology Paradox (PO Dated After Invoice)...")
    docs = get_base_clean_documents()
    # PO date 2024-02-15 occurs after Invoice date 2024-01-15
    docs["Purchase Order"]["po_date"] = "2024-02-15"

    report = FraudDetectionEngine.audit_extracted_documents(docs)

    chrono_anomalies = [a for a in report.anomalies if a.anomaly_id == "FRD_DATE_PO_INV_011"]
    assert len(chrono_anomalies) == 1, "Expected temporal paradox anomaly"
    assert chrono_anomalies[0].category == AnomalyCategory.TEMPORAL_PARADOX
    assert chrono_anomalies[0].severity == AnomalySeverity.HIGH
    print(f"      Passed! Flagged {chrono_anomalies[0].anomaly_id}: {chrono_anomalies[0].evidence}.")


def test_digital_pdf_metadata_inspection():
    print("[6/7] Testing Digital PDF File Inspection on Uploaded Sample...")
    # Find any existing sample PDF in uploads/
    uploads_dir = Path(WORKSPACE_ROOT) / "uploads"
    pdf_files = list(uploads_dir.glob("*.pdf")) if uploads_dir.exists() else []

    if pdf_files:
        sample_pdf = pdf_files[0]
        res = inspect_pdf_forensics(sample_pdf, filename=sample_pdf.name)
        assert res.page_count >= 1
        assert res.filename == sample_pdf.name
        print(f"      Passed! Inspected '{sample_pdf.name}' ({res.page_count} pages, {len(res.fonts_detected)} fonts).")
    else:
        # Synthesize in-memory test PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(fitz.Point(50, 50), "Authentic Customs Invoice")
        pdf_bytes = doc.write()
        doc.close()
        res = inspect_pdf_forensics(pdf_bytes, filename="test_synthetic.pdf")
        assert res.page_count == 1
        print("      Passed! Synthetic PDF forensic inspection verified.")


def test_fraud_controller_integration():
    print("[7/7] Testing FraudController.inspect_documents() serialization...")
    docs = get_base_clean_documents()
    req = InspectDocumentsRequest(
        documents=docs,
        scenario_title="Clean Industrial Export",
    )
    report = FraudController.inspect_documents(req)

    assert report.audit_id.startswith("frd_")
    assert report.overall_risk_level == FraudRiskLevel.GENUINE
    assert len(report.document_breakdown) >= 4
    print(f"      Passed! Serialized FraudAnalysisReport ({report.audit_id}).")


def main():
    print("======================================================================")
    print("TASK 6: FAKE DOCUMENT & TAMPER DETECTION VERIFICATION SUITE")
    print("======================================================================")
    test_clean_authentic_shipment()
    test_fabricated_gstin_checksum_forgery()
    test_line_item_math_manipulation()
    test_physical_weight_inversion()
    test_temporal_chronology_paradox()
    test_digital_pdf_metadata_inspection()
    test_fraud_controller_integration()
    print("======================================================================")
    print("ALL 7 FAKE DOCUMENT DETECTION TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")


if __name__ == "__main__":
    main()
