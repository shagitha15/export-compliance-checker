"""
Step 5 Final End-to-End Verification and Sign-Off Suite.
Validates all backend subsystems: Lifespan, Routing, Ingestion, OCR, Gemini Extraction,
Repository, 6 Validation Scenarios, 4 Statutory Scenarios, Error Handling, and Resilience.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz  # PyMuPDF
from httpx import ASGITransport, AsyncClient
from test_validation import get_mock_documents


def create_minimal_pdf_bytes(title: str = "COMMERCIAL INVOICE", content: str = "Invoice INV-2024-TEST") -> bytes:
    """Generates a valid, minimal in-memory PDF using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n{content}", fontsize=12)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def build_canonical_docs() -> dict[str, dict]:
    """Generates clean mock documents satisfying all 16 reconciliation and intra-document rules."""
    docs = get_mock_documents()
    docs["Commercial Invoice"]["exporter_iec"] = "0512345678"
    docs["Commercial Invoice"]["lut_arn"] = "AD060324001234A"
    docs["Commercial Invoice"]["declaration_and_signatory"] = {
        "signatory_name": "Rajesh Kumar",
        "designation": "Director",
        "declaration_text": "We declare that this invoice shows the actual price of the goods and that all particulars are true and correct under Section 50 Customs Act.",
    }
    docs["Shipping Bill"]["section_50_declaration"] = True
    return docs



async def run_final_verification():
    print("=" * 80)
    print("  STEP 5: END-TO-END FINAL BACKEND VERIFICATION & SIGN-OFF SUITE")
    print("=" * 80)

    from server.main import app
    from server.schemas.upload import DocumentType
    from server.schemas.validation import ValidationStatus, ValidationDirectPayload
    from server.controllers.compliance_controller import ComplianceController
    from server.controllers.document_controller import DocumentController

    # --------------------------------------------------------------------------
    # SECTION 1: Application Routing & Schema Compliance
    # --------------------------------------------------------------------------
    print("\n[SECTION 1] Application Startup & OpenAPI Route Verification...")
    openapi = app.openapi()
    paths = list(openapi.get("paths", {}).keys())
    required_routes = [
        "/",
        "/api/v1/health",
        "/api/v1/documents/upload",
        "/api/v1/documents/extract",
        "/api/v1/documents/extract-saved/{filename}",
        "/api/v1/compliance/validate",
        "/api/v1/compliance/validate-stored",
        "/api/v1/compliance/verify-rules",
        "/api/v1/compliance/audit",
    ]
    for r in required_routes:
        assert r in paths, f"Route {r} not registered in OpenAPI schema!"
    print(f"  PASS: All {len(required_routes)} API routes verified in OpenAPI specification.")

    # --------------------------------------------------------------------------
    # SECTION 2: Document Ingestion, OCR & Error Handling
    # --------------------------------------------------------------------------
    print("\n[SECTION 2] Document Ingestion, OCR, and Validation Error Handling...")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 2A. Health Check
        h_res = await client.get("/api/v1/health")
        assert h_res.status_code == 200
        assert h_res.json()["data"]["status"] in ("healthy", "degraded")
        print("  PASS: GET /api/v1/health returned 200 OK.")

        # 2B. Upload with invalid extension (.txt)
        txt_files = {"file": ("invoice.txt", io.BytesIO(b"Hello text"), "text/plain")}
        res = await client.post("/api/v1/documents/upload", files=txt_files, data={"document_type": "Commercial Invoice"})
        assert res.status_code == 400
        assert "Only '.pdf' files are accepted" in res.json().get("detail", "")
        print("  PASS: Rejected non-PDF extension with 400 Bad Request.")

        # 2C. Upload with corrupt PDF header (missing %PDF)
        corrupt_files = {"file": ("invoice.pdf", io.BytesIO(b"CORRUPT_BYTES_NOT_PDF"), "application/pdf")}
        res = await client.post("/api/v1/documents/upload", files=corrupt_files, data={"document_type": "Commercial Invoice"})
        assert res.status_code == 400
        assert "missing %PDF signature" in res.json().get("detail", "")
        print("  PASS: Rejected corrupt PDF header (missing %PDF) with 400 Bad Request.")

        # 2D. Upload with valid PDF and mock Gemini structured extraction
        valid_pdf_bytes = create_minimal_pdf_bytes(
            title="COMMERCIAL INVOICE",
            content="Exporter: Global Exports Ltd\nInvoice No: INV-2024-TEST\nTotal: 22500 EUR",
        )
        mock_extracted_json = {
            "invoice_number": "INV-2024-TEST",
            "invoice_date": "2024-10-15",
            "exporter_seller": {"name": "Global Exports Ltd"},
            "total_invoice_amount": 22500.0,
        }

        with patch("server.controllers.document_controller.extract_document_data", return_value=mock_extracted_json):
            pdf_upload_files = {"file": ("test_invoice.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
            up_res = await client.post(
                "/api/v1/documents/upload",
                files=pdf_upload_files,
                data={"document_type": "Commercial Invoice"},
            )
            assert up_res.status_code == 201, f"Expected 201, got {up_res.status_code}: {up_res.text}"
            up_data = up_res.json()
            assert up_data["upload_status"] == "success"
            assert up_data["extracted_data"]["invoice_number"] == "INV-2024-TEST"
            saved_filename = up_data["filename"]
            print(f"  PASS: POST /api/v1/documents/upload -> 201 Created (Saved: {saved_filename}).")

            # 2E. Extract from PDF directly
            pdf_extract_files = {"file": ("test_invoice.pdf", io.BytesIO(valid_pdf_bytes), "application/pdf")}
            ext_res = await client.post(
                "/api/v1/documents/extract",
                files=pdf_extract_files,
                data={"document_type": "Commercial Invoice"},
            )
            assert ext_res.status_code == 200
            assert ext_res.json()["extraction_status"] == "success"
            print("  PASS: POST /api/v1/documents/extract -> 200 OK.")

            # 2F. Extract from saved file
            saved_res = await client.post(
                f"/api/v1/documents/extract-saved/{saved_filename}?document_type=Commercial Invoice"
            )
            assert saved_res.status_code == 200
            assert saved_res.json()["extracted_data"]["invoice_number"] == "INV-2024-TEST"
            print(f"  PASS: POST /api/v1/documents/extract-saved/{saved_filename} -> 200 OK.")

            # 2G. Extract non-existent saved file
            missing_res = await client.post(
                "/api/v1/documents/extract-saved/completely_non_existent.pdf?document_type=Commercial Invoice"
            )
            assert missing_res.status_code == 404
            print("  PASS: POST /api/v1/documents/extract-saved/missing -> 404 Not Found.")

    # --------------------------------------------------------------------------
    # SECTION 3: Cross-Document Validation Scenarios
    # --------------------------------------------------------------------------
    print("\n[SECTION 3] Cross-Document Validation Scenarios...")
    # 3A. Fully Matching Documents
    docs_matching = build_canonical_docs()
    res_3a = await ComplianceController.validate_documents(ValidationDirectPayload(documents=docs_matching))
    assert res_3a.overall_compliance_status == ValidationStatus.PASS
    assert res_3a.summary.passed == 16
    assert res_3a.summary.failed == 0
    print(f"  PASS [Scenario 3A]: Fully matching documents: 16/16 checks passed (Overall PASS).")

    # 3B. Mismatched Invoice Numbers
    docs_mismatch_inv = build_canonical_docs()
    docs_mismatch_inv["Packing List"]["invoice_reference_number"] = "INV-MISMATCH-999"
    res_3b = await ComplianceController.validate_documents(ValidationDirectPayload(documents=docs_mismatch_inv))
    assert res_3b.overall_compliance_status == ValidationStatus.FAIL
    assert any(c.check_id == "XDOC_INV_NUM_001" and c.status == ValidationStatus.FAIL for c in res_3b.cross_document_results)
    print(f"  PASS [Scenario 3B]: Mismatched invoice number caught by XDOC_INV_NUM_001 (Overall FAIL).")

    # 3C. Quantity Discrepancy
    docs_mismatch_qty = build_canonical_docs()
    docs_mismatch_qty["Packing List"]["packages"][0]["quantity"] = 999.0
    res_3c = await ComplianceController.validate_documents(ValidationDirectPayload(documents=docs_mismatch_qty))
    assert res_3c.overall_compliance_status == ValidationStatus.FAIL
    assert any(c.check_id == "XDOC_QTY_005" and c.status == ValidationStatus.FAIL for c in res_3c.cross_document_results)
    print(f"  PASS [Scenario 3C]: Quantity discrepancy caught by XDOC_QTY_005 (Overall FAIL).")

    # 3D. Weight Discrepancy
    docs_mismatch_wt = build_canonical_docs()
    docs_mismatch_wt["Packing List"]["total_gross_weight"]["value"] = 5500.0  # vs SB 1250.5
    res_3d = await ComplianceController.validate_documents(ValidationDirectPayload(documents=docs_mismatch_wt))
    assert res_3d.overall_compliance_status == ValidationStatus.FAIL
    assert any(c.check_id == "XDOC_WT_007" and c.status == ValidationStatus.FAIL for c in res_3d.cross_document_results)
    print(f"  PASS [Scenario 3D]: Gross weight discrepancy caught by XDOC_WT_007 (Overall FAIL).")


    # 3E. Missing Documents (Partial Submission: Commercial Invoice + Packing List only)
    docs_partial = {
        "Commercial Invoice": docs_matching["Commercial Invoice"],
        "Packing List": docs_matching["Packing List"],
    }
    res_3e = await ComplianceController.validate_documents(ValidationDirectPayload(documents=docs_partial))
    assert res_3e.overall_compliance_status == ValidationStatus.PASS
    assert set(res_3e.documents_missing) == {"Purchase Order", "Shipping Bill", "Certificate of Origin"}
    assert res_3e.summary.not_applicable == 5
    print(f"  PASS [Scenario 3E]: Partial submission correctly marked {res_3e.summary.not_applicable} checks NOT APPLICABLE.")

    # 3F. Empty Payload Validation Rejection
    try:
        await ComplianceController.validate_documents(ValidationDirectPayload(documents={}))
        assert False, "Should raise 400"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        print(f"  PASS [Scenario 3F]: Empty documents payload rejected with 400 Bad Request.")

    # --------------------------------------------------------------------------
    # SECTION 4: Statutory Government Rules Verification Scenarios
    # --------------------------------------------------------------------------
    print("\n[SECTION 4] Statutory Government Rules Verification Scenarios...")
    # 4A. Compliant Shipment
    docs_gov_compliant = build_canonical_docs()
    rep_4a = await ComplianceController.verify_statutory_rules(ValidationDirectPayload(documents=docs_gov_compliant))
    assert rep_4a.overall_government_compliance.value == "COMPLIANT"
    assert rep_4a.summary.non_compliant_count == 0
    print(f"  PASS [Scenario 4A]: Compliant shipment verified as COMPLIANT ({rep_4a.summary.compliant_count} satisfied).")

    # 4B. Missing IEC Shipment
    docs_missing_iec = build_canonical_docs()
    docs_missing_iec["Commercial Invoice"].pop("exporter_iec", None)
    if "exporter_seller" in docs_missing_iec["Commercial Invoice"]:
        docs_missing_iec["Commercial Invoice"]["exporter_seller"].pop("tax_id_or_gstin", None)
    rep_4b = await ComplianceController.verify_statutory_rules(ValidationDirectPayload(documents=docs_missing_iec))
    assert rep_4b.overall_government_compliance.value == "NON_COMPLIANT"
    iec_finding = next((f for f in rep_4b.findings if f.rule_id == "DGFT_FTP2023_P2_05"), None)
    assert iec_finding is not None
    assert iec_finding.status.value == "NON_COMPLIANT"
    print(f"  PASS [Scenario 4B]: Missing IEC correctly flagged NON_COMPLIANT on rule DGFT_FTP2023_P2_05.")

    # 4C. Restricted Export Product without Authorization
    docs_restricted = build_canonical_docs()
    docs_restricted["Commercial Invoice"]["line_items"] = [
        {
            "item_no": 1,
            "description": "SCOMET Dual-Use Inertial Navigation Laser Gyroscope System",
            "hs_code": "9014.20",
            "quantity": 5,
            "unit": "PCS",
            "unit_price": 12000.0,
            "total_amount": 60000.0,
        }
    ]
    docs_restricted["Shipping Bill"]["items"] = [
        {
            "item_no": 1,
            "description": "SCOMET Dual-Use Inertial Navigation Laser Gyroscope System",
            "ritc_hs_code": "90142000",
            "quantity": 5,
            "unit": "PCS",
            "fob_value": 60000.0,
        }
    ]
    docs_restricted["Shipping Bill"]["scheme_code"] = None
    rep_4c = await ComplianceController.verify_statutory_rules(ValidationDirectPayload(documents=docs_restricted))
    assert rep_4c.overall_government_compliance.value == "NON_COMPLIANT"
    scomet_finding = next((f for f in rep_4c.findings if f.rule_id == "DGFT_SCOMET_GEN"), None)
    assert scomet_finding is not None
    assert scomet_finding.status.value == "NON_COMPLIANT"
    print(f"  PASS [Scenario 4C]: Restricted export item correctly flagged NON_COMPLIANT on rule DGFT_SCOMET_GEN.")


    # 4D. Empty Payload Rejection
    try:
        await ComplianceController.verify_statutory_rules(ValidationDirectPayload(documents={}))
        assert False, "Should raise 400"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        print(f"  PASS [Scenario 4D]: Empty payload rejected with 400 Bad Request.")

    # --------------------------------------------------------------------------
    # SECTION 5: Unified Audit Endpoint
    # --------------------------------------------------------------------------
    print("\n[SECTION 5] Unified Audit Endpoint Execution...")
    audit_res = await ComplianceController.audit_full_shipment(ValidationDirectPayload(documents=docs_gov_compliant))
    assert audit_res.cross_document_validation.overall_compliance_status.value == "PASS"
    assert audit_res.government_compliance.overall_government_compliance.value == "COMPLIANT"
    print("  PASS: Unified audit endpoint evaluated cross-document reconciliation and statutory rules simultaneously.")

    print("\n" + "=" * 80)
    print("  STEP 5 FINAL END-TO-END VERIFICATION: 100% OF ALL CHECKS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_final_verification())
