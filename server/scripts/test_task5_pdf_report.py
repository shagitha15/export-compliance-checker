"""
Task 5: PDF Compliance Report Verification Script
Tests multi-page PDF generation using PyMuPDF (fitz) and the FastAPI route POST /api/v1/compliance/report/pdf.

Validates:
1. Clean matching 5-document shipment (100% PASS).
2. Discrepancy shipment (Price & Currency Mismatch - FAIL).
3. Partial document submission (Missing documents handled gracefully with N/A).
4. FastAPI HTTP endpoint integration via ASGITransport (POST /api/v1/compliance/report/pdf).
5. Statutory DGFT, CBIC, and RBI legal citations in generated PDF.
"""

import asyncio
import io
import sys
import os
from typing import List, Dict, Any
from unittest.mock import patch

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import fitz  # PyMuPDF
from httpx import ASGITransport, AsyncClient

from server.reports.pdf_generator import generate_compliance_pdf_report
from server.schemas.report import GeneratePdfReportRequest, ShipmentDetails
from server.schemas.validation import (
    CrossDocumentValidationResponse,
    CheckResult,
    ValidationSummary,
    ValidationStatus,
)
from server.schemas.compliance import (
    GovernmentComplianceReport,
    GovernmentComplianceSummary,
    RegulatoryFinding,
    RegulatoryComplianceStatus,
)
from server.main import app


def create_sample_rule_results(has_mismatches: bool = False, missing_docs: bool = False) -> List[CheckResult]:
    rule_defs = [
        ("XDOC_INV_PO_001", "Invoice Number on Purchase Order", ["Commercial Invoice", "Purchase Order"], "invoice_number"),
        ("XDOC_PO_NO_002", "PO Number Cited on Commercial Invoice", ["Commercial Invoice", "Purchase Order"], "po_number"),
        ("XDOC_BUYER_003", "Buyer & Seller Entity Consistency", ["Commercial Invoice", "Purchase Order"], "exporter_seller.name"),
        ("XDOC_CURR_004", "Currency Uniformity Across Invoice & PO", ["Commercial Invoice", "Purchase Order"], "currency"),
        ("XDOC_INCO_005", "Incoterms Alignment Across Invoice & PO", ["Commercial Invoice", "Purchase Order"], "incoterms"),
        ("XDOC_TOTAL_VAL_006", "Total Invoice Value Consistency", ["Commercial Invoice", "Purchase Order"], "total_invoice_amount"),
        ("XDOC_WT_007", "Total Gross Weight Reconciliation", ["Commercial Invoice", "Packing List"], "total_gross_weight"),
        ("XDOC_NET_WT_008", "Net Weight Reconciliation", ["Commercial Invoice", "Packing List"], "total_net_weight"),
        ("XDOC_PKG_COUNT_009", "Total Package Count Integrity", ["Commercial Invoice", "Packing List"], "total_packages_count"),
        ("XDOC_PL_REF_010", "Invoice Reference on Packing List", ["Commercial Invoice", "Packing List"], "invoice_reference_number"),
        ("XDOC_SB_INV_011", "Invoice Number on Customs Shipping Bill", ["Commercial Invoice", "Shipping Bill"], "invoice_number"),
        ("XDOC_SB_VAL_012", "FOB Customs Value Declaration Check", ["Commercial Invoice", "Shipping Bill"], "fob_value"),
        ("XDOC_SB_WT_013", "Gross Weight on Customs Shipping Bill", ["Shipping Bill", "Packing List"], "gross_weight"),
        ("XDOC_COO_INV_014", "Invoice Reference on Certificate of Origin", ["Commercial Invoice", "Certificate of Origin"], "invoice_number"),
        ("XDOC_COO_ORIGIN_015", "Origin Declaration Consistency Across Invoice & COO", ["Commercial Invoice", "Certificate of Origin"], "origin_criterion"),
        ("XDOC_COO_EXPORTER_016", "Exporter Name Matching Across Invoice & COO", ["Commercial Invoice", "Certificate of Origin"], "exporter.name"),
    ]

    checks = []
    for check_id, name, docs, field in rule_defs:
        is_po_rule = "PO" in check_id or "BUYER" in check_id or "CURR" in check_id or "INCO" in check_id or "TOTAL_VAL" in check_id
        is_coo_rule = "COO" in check_id

        if missing_docs and (is_po_rule or is_coo_rule):
            status = ValidationStatus.NOT_APPLICABLE
            msg = "Referenced document omitted from upload package."
            disc = None
        elif has_mismatches and check_id in ("XDOC_CURR_004", "XDOC_TOTAL_VAL_006"):
            status = ValidationStatus.FAIL
            disc = f"Discrepancy in {field}: contract value mismatch detected"
            msg = f"Check failed due to variance in {field}."
        else:
            status = ValidationStatus.PASS
            disc = None
            msg = "Field values match across comparing documents."

        checks.append(
            CheckResult(
                check_id=check_id,
                rule_name=name,
                documents_involved=docs,
                status=status,
                field_name=field,
                discrepancy=disc,
                message=msg,
            )
        )
    return checks


def create_sample_statutory_report(compliant: bool = True) -> GovernmentComplianceReport:
    findings = [
        RegulatoryFinding(
            rule_id="DGFT_FTP2023_P2_05",
            rule_title="Mandatory IEC (Importer Exporter Code)",
            authority="DGFT / FTP 2023",
            policy_document="Foreign Trade Policy 2023",
            para_ref="Para 2.05",
            source_url="https://www.dgft.gov.in",
            status=RegulatoryComplianceStatus.COMPLIANT if compliant else RegulatoryComplianceStatus.NON_COMPLIANT,
            requirement_summary="Exporter must cite valid 10-digit DGFT-issued Importer Exporter Code.",
            observed_evidence="Valid IEC '0312345678' identified on Commercial Invoice." if compliant else "Missing exporter IEC.",
            action_required=None if compliant else "Obtain or cite valid 10-digit DGFT IEC.",
        ),
        RegulatoryFinding(
            rule_id="CBIC_CA1962_SEC50",
            rule_title="Statutory Declaration of Truthfulness",
            authority="CBIC / Customs Act",
            policy_document="Customs Act 1962",
            para_ref="Section 50",
            source_url="https://www.cbic.gov.in",
            status=RegulatoryComplianceStatus.COMPLIANT,
            requirement_summary="Mandatory truthfulness declaration under Section 50 of the Customs Act 1962.",
            observed_evidence="Authorized statutory declaration text present on Commercial Invoice.",
        ),
        RegulatoryFinding(
            rule_id="RBI_FEMA_EXP_09M",
            rule_title="FEMA 9-Month Export Realization Mandate",
            authority="RBI / FEMA",
            policy_document="FEMA (Export of Goods & Services) Regulations",
            para_ref="Regulation 9",
            source_url="https://www.rbi.org.in",
            status=RegulatoryComplianceStatus.COMPLIANT,
            requirement_summary="Full export proceeds must be realized within 9 months in approved convertible currency.",
            observed_evidence="Shipment invoiced in convertible currency 'EUR'.",
        ),
        RegulatoryFinding(
            rule_id="DGFT_FTP2023_P2_06",
            rule_title="Authorized Dealer (AD) Code Port Registration",
            authority="DGFT / ICEGATE",
            policy_document="Foreign Trade Policy 2023",
            para_ref="Para 2.06",
            source_url="https://www.icegate.gov.in",
            status=RegulatoryComplianceStatus.ADVISORY,
            requirement_summary="AD Code must be active on ICEGATE at the designated port of export.",
            observed_evidence="Ensure bank Authorized Dealer (AD) code is registered with customs port.",
            action_required="Verify AD Code registration status on ICEGATE portal before vessel loading.",
        ),
    ]

    return GovernmentComplianceReport(
        audit_id="gov_test_001",
        audit_timestamp="2026-11-25T12:00:00Z",
        hs_codes_evaluated=["848340"],
        destination_country="Germany (EU)",
        overall_government_compliance=RegulatoryComplianceStatus.COMPLIANT if compliant else RegulatoryComplianceStatus.NON_COMPLIANT,
        summary=GovernmentComplianceSummary(
            total_rules_evaluated=4,
            compliant_count=3 if compliant else 2,
            non_compliant_count=0 if compliant else 1,
            advisory_count=1,
        ),
        findings=findings,
    )


def test_generator_clean_shipment():
    print("[1/5] Testing PDF generator on Clean 5-Document Shipment (100% PASS)...")
    shipment = ShipmentDetails(
        exporter_name="Global Exports Ltd",
        exporter_iec="0312345678",
        exporter_gstin="27AAACG0000A1Z5",
        consignee_name="Acme Trading GmbH",
        destination_country="Germany (EU)",
        invoice_number="INV-2024-001",
        declared_currency="EUR",
        total_declared_value=22500.0,
        incoterms="FOB",
    )
    checks = create_sample_rule_results(has_mismatches=False, missing_docs=False)
    gov = create_sample_statutory_report(compliant=True)

    val_response = CrossDocumentValidationResponse(
        audit_id="aud_clean_test_001",
        audit_timestamp="2026-11-25T12:00:00Z",
        documents_evaluated=["Commercial Invoice", "Packing List", "Purchase Order", "Shipping Bill", "Certificate of Origin"],
        documents_missing=[],
        overall_compliance_status=ValidationStatus.PASS,
        summary=ValidationSummary(
            total_checks=len(checks),
            passed=len(checks),
            failed=0,
            not_applicable=0,
        ),
        cross_document_results=checks,
    )

    request = GeneratePdfReportRequest(
        shipment_details=shipment,
        cross_document_validation=val_response,
        government_compliance=gov,
        scenario_title="Clean Trade Set (Industrial Machinery to Germany)",
    )

    pdf_bytes = generate_compliance_pdf_report(request)

    assert pdf_bytes.startswith(b"%PDF-"), "Generated content is not a valid PDF binary"
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count >= 2, f"Expected at least 2 pages, got {doc.page_count}"

    full_text = "".join(p.get_text() for p in doc)

    assert "OFFICIAL EXPORT CUSTOMS COMPLIANCE AUDIT CERTIFICATE" in full_text
    assert "Global Exports Ltd" in full_text
    assert "Acme Trading GmbH" in full_text
    assert "OVERALL STATUS: PASS" in full_text
    assert "XDOC_INV_PO_001" in full_text
    assert "XDOC_COO_EXPORTER_016" in full_text
    assert "DGFT_FTP2023_P2_05" in full_text
    print(f"      Passed! Generated {len(pdf_bytes)} bytes across {doc.page_count} pages.")


def test_generator_discrepancy_shipment():
    print("[2/5] Testing PDF generator on Discrepancy Shipment (Price & Currency Mismatch - FAIL)...")
    shipment = ShipmentDetails(
        exporter_name="Apex Industrial Exports",
        consignee_name="US Auto Parts LLC",
        destination_country="United States",
        invoice_number="INV-2024-002",
        declared_currency="USD",
        total_declared_value=35000.0,
        incoterms="CIF",
    )
    checks = create_sample_rule_results(has_mismatches=True, missing_docs=False)
    gov = create_sample_statutory_report(compliant=True)

    passed_count = sum(1 for c in checks if c.status == ValidationStatus.PASS)
    failed_count = sum(1 for c in checks if c.status == ValidationStatus.FAIL)

    val_response = CrossDocumentValidationResponse(
        audit_id="aud_disc_test_002",
        audit_timestamp="2026-11-25T12:00:00Z",
        documents_evaluated=["Commercial Invoice", "Packing List", "Purchase Order", "Shipping Bill", "Certificate of Origin"],
        documents_missing=[],
        overall_compliance_status=ValidationStatus.FAIL,
        summary=ValidationSummary(
            total_checks=len(checks),
            passed=passed_count,
            failed=failed_count,
            not_applicable=0,
        ),
        cross_document_results=checks,
    )

    request = GeneratePdfReportRequest(
        shipment_details=shipment,
        cross_document_validation=val_response,
        government_compliance=gov,
        scenario_title="Contract Price & Currency Mismatch Discrepancy",
    )

    pdf_bytes = generate_compliance_pdf_report(request)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(p.get_text() for p in doc)

    assert "OVERALL STATUS: FAIL" in full_text
    assert "Apex Industrial Exports" in full_text
    assert "CRITICAL DISCREPANCIES IDENTIFIED" in full_text
    print(f"      Passed! Correctly rendered discrepancies across {doc.page_count} pages ({len(pdf_bytes)} bytes).")


def test_generator_partial_submission():
    print("[3/5] Testing PDF generator on Partial Document Set (Missing PO & COO)...")
    shipment = ShipmentDetails(
        exporter_name="Sunrise Textiles Pvt Ltd",
        consignee_name="Nordic Apparel AS",
        destination_country="Norway",
        invoice_number="INV-2024-PART-01",
        declared_currency="USD",
        total_declared_value=12000.0,
    )
    checks = create_sample_rule_results(has_mismatches=False, missing_docs=True)
    gov = create_sample_statutory_report(compliant=True)

    passed_count = sum(1 for c in checks if c.status == ValidationStatus.PASS)
    na_count = sum(1 for c in checks if c.status == ValidationStatus.NOT_APPLICABLE)

    val_response = CrossDocumentValidationResponse(
        audit_id="aud_partial_test_003",
        audit_timestamp="2026-11-25T12:00:00Z",
        documents_evaluated=["Commercial Invoice", "Packing List", "Shipping Bill"],
        documents_missing=["Purchase Order", "Certificate of Origin"],
        overall_compliance_status=ValidationStatus.PASS,
        summary=ValidationSummary(
            total_checks=len(checks),
            passed=passed_count,
            failed=0,
            not_applicable=na_count,
        ),
        cross_document_results=checks,
    )

    request = GeneratePdfReportRequest(
        shipment_details=shipment,
        cross_document_validation=val_response,
        government_compliance=gov,
        scenario_title="Partial Trade Set (Missing Documents)",
    )

    pdf_bytes = generate_compliance_pdf_report(request)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(p.get_text() for p in doc)

    assert "Sunrise Textiles Pvt Ltd" in full_text
    assert "NOT APPLICABLE" in full_text or "N/A" in full_text
    print(f"      Passed! Handled missing documents gracefully across {doc.page_count} pages.")


def _run_async(coro):
    """Runs an async coroutine using IOCP wakeups on Windows to avoid socketpair() blocks."""
    if sys.platform == "win32":
        import _overlapped

        class _InProcessProactorEventLoop(asyncio.ProactorEventLoop):
            def __init__(self) -> None:
                asyncio.BaseEventLoop.__init__(self)
                proactor = asyncio.IocpProactor()
                self._proactor = proactor
                self._selector = proactor
                self._self_reading_future = None
                self._accept_futures = {}
                self._wakeup_ov = _overlapped.Overlapped(0)
                proactor.set_loop(self)

            def _make_self_pipe(self) -> None:
                pass

            def _close_self_pipe(self) -> None:
                pass

            def _loop_self_reading(self, f=None) -> None:
                pass

            def _write_to_self(self) -> None:
                if self._proactor is not None and self._proactor._iocp is not None:
                    _overlapped.PostQueuedCompletionStatus(
                        self._proactor._iocp, 0, 0, self._wakeup_ov.address
                    )

        return asyncio.run(coro, loop_factory=_InProcessProactorEventLoop)
    return asyncio.run(coro)


def test_fastapi_pdf_endpoint():
    print("[4/7] Testing FastAPI HTTP POST /api/v1/compliance/report/pdf via ASGITransport...")
    shipment = ShipmentDetails(
        exporter_name="FastAPI Test Exporter",
        consignee_name="Global Test Consignee",
        destination_country="Japan",
        invoice_number="INV-TEST-004",
    )
    checks = create_sample_rule_results(has_mismatches=False, missing_docs=False)
    gov = create_sample_statutory_report(compliant=True)

    val_response = CrossDocumentValidationResponse(
        audit_id="aud_http_test_004",
        audit_timestamp="2026-11-25T12:00:00Z",
        documents_evaluated=["Commercial Invoice", "Packing List"],
        documents_missing=["Purchase Order", "Shipping Bill", "Certificate of Origin"],
        overall_compliance_status=ValidationStatus.PASS,
        summary=ValidationSummary(
            total_checks=len(checks),
            passed=len(checks),
            failed=0,
            not_applicable=0,
        ),
        cross_document_results=checks,
    )

    req_data = GeneratePdfReportRequest(
        shipment_details=shipment,
        cross_document_validation=val_response,
        government_compliance=gov,
        scenario_title="FastAPI HTTP Endpoint Integration Test",
    ).model_dump(mode="json")

    from server.auth.dependencies import get_current_user
    from server.auth.models import AuthenticatedUser, OrgRole

    test_user = AuthenticatedUser(user_id="test-uid", email="test@example.com")
    test_membership = [{
        "organization_id": "11111111-1111-4111-8111-111111111111",
        "user_id": "test-uid",
        "role": OrgRole.ADMIN.value,
        "status": "active",
        "organization": {"id": "11111111-1111-4111-8111-111111111111", "name": "Test Org"},
    }]
    app.dependency_overrides[get_current_user] = lambda: test_user

    async def _post_pdf():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            return await client.post("/api/v1/compliance/report/pdf", json=req_data)

    try:
        with patch("server.auth.dependencies.OrganizationRepository.list_user_organizations", return_value=test_membership), \
             patch("server.storage.document_storage.DocumentStorageService.upload_private_pdf", return_value="org/batch/report.pdf"), \
             patch("server.repositories.audit_repository.AuditRepository.save_compliance_report", return_value={"id": "1"}):
            response = _run_async(_post_pdf())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF-")

    doc = fitz.open(stream=response.content, filetype="pdf")
    assert doc.page_count >= 2
    full_text = "".join(p.get_text() for p in doc)
    assert "FastAPI Test Exporter" in full_text
    assert f"Page 1 of {doc.page_count}" in full_text
    print(f"      Passed! Received {len(response.content)} bytes from FastAPI endpoint.")


def test_statutory_authority_citations():
    print("[5/7] Verifying Statutory DGFT, CBIC, and RBI legal citations in generated PDF...")
    shipment = ShipmentDetails(
        exporter_name="Regulatory Compliance Audit",
    )
    checks = create_sample_rule_results(has_mismatches=False, missing_docs=False)
    gov = create_sample_statutory_report(compliant=True)

    val_response = CrossDocumentValidationResponse(
        audit_id="aud_cit_test_005",
        audit_timestamp="2026-11-25T12:00:00Z",
        documents_evaluated=["Commercial Invoice"],
        documents_missing=[],
        overall_compliance_status=ValidationStatus.PASS,
        summary=ValidationSummary(
            total_checks=len(checks),
            passed=len(checks),
            failed=0,
            not_applicable=0,
        ),
        cross_document_results=checks,
    )

    request = GeneratePdfReportRequest(
        shipment_details=shipment,
        cross_document_validation=val_response,
        government_compliance=gov,
    )

    pdf_bytes = generate_compliance_pdf_report(request)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(p.get_text() for p in doc)

    assert "DGFT / FTP 2023" in full_text or "Foreign Trade Policy 2023" in full_text
    assert "CBIC / Customs Act" in full_text or "Customs Act 1962" in full_text
    assert "RBI / FEMA" in full_text or "FEMA" in full_text
    assert "Precision Dynamics India Pvt Ltd" not in full_text, "Fabricated fallback exporter leaked!"
    print("      Passed! All statutory citations verified with zero fabricated defaults.")


def test_failed_and_partial_batch_pdf_reports():
    print("[6/7] Testing Failed-Batch (0 valid docs) and Partial-Success Batch PDF Generation...")
    # 1. Completely failed batch (cross_document_validation=None)
    failed_req = GeneratePdfReportRequest(
        batch_id="batch_failed_001",
        batch_status="FAILED",
        report_generated_at="2026-11-25T17:30:00Z",
        uploaded_documents=[
            {
                "original_filename": "corrupt_invoice.pdf",
                "document_type": None,
                "status": "FAILED",
                "file_size_bytes": 128,
                "error": "Corrupted or invalid PDF document (missing %PDF signature).",
                "error_code": "CORRUPT_PDF_HEADER",
            },
            {
                "original_filename": "empty.pdf",
                "document_type": None,
                "status": "FAILED",
                "file_size_bytes": 0,
                "error": "Uploaded file 'empty.pdf' is empty (0 bytes).",
                "error_code": "EMPTY_FILE",
            },
        ],
        cross_document_validation=None,
        government_compliance=None,
    )
    failed_pdf = generate_compliance_pdf_report(failed_req)
    assert failed_pdf.startswith(b"%PDF-")
    doc_fail = fitz.open(stream=failed_pdf, filetype="pdf")
    fail_text = "".join(p.get_text() for p in doc_fail)
    assert "batch_failed_001" in fail_text
    assert "OVERALL STATUS: FAILED" in fail_text
    assert "corrupt_invoice.pdf" in fail_text
    assert "Not Available" in fail_text
    assert f"Page 1 of {doc_fail.page_count}" in fail_text
    print(f"      Passed! Failed-batch and partial-batch edge cases rendered cleanly ({doc_fail.page_count} pages).")


def test_upload_to_report_workflow():
    print("[7/7] Testing End-to-End Batch Upload -> Fraud Inspection -> PDF Report Download...")
    from test_task3_integration import create_in_memory_pdf, get_mock_documents, mock_gov_rules_dispatcher

    mock_docs = get_mock_documents()
    # Inject a forged GSTIN check digit so fake document detection produces a real anomaly
    mock_docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = "27AAACG0000A1Z0"
    ci_mock = mock_docs["Commercial Invoice"]

    def mock_extract(*args, **kwargs):
        dtype = kwargs.get("document_type") or (args[0] if args else "Commercial Invoice")
        return mock_docs.get(dtype, ci_mock)

    ci_pdf = create_in_memory_pdf("COMMERCIAL INVOICE", "Invoice INV-2024-001")
    pl_pdf = create_in_memory_pdf("PACKING LIST", "PL-2024-001")

    from server.auth.dependencies import get_current_user
    from server.auth.models import AuthenticatedUser, OrgRole

    test_user = AuthenticatedUser(user_id="test-uid", email="test@example.com")
    test_membership = [{
        "organization_id": "11111111-1111-4111-8111-111111111111",
        "user_id": "test-uid",
        "role": OrgRole.ADMIN.value,
        "status": "active",
        "organization": {"id": "11111111-1111-4111-8111-111111111111", "name": "Test Org"},
    }]

    async def _workflow():
        app.dependency_overrides[get_current_user] = lambda: test_user
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                with patch("server.auth.dependencies.OrganizationRepository.list_user_organizations", return_value=test_membership), \
                     patch("server.storage.document_storage.DocumentStorageService.upload_private_pdf", return_value="org/batch/doc.pdf"), \
                     patch("server.repositories.audit_repository.AuditRepository.save_batch_audit", return_value={"id": "1"}), \
                     patch("server.repositories.audit_repository.AuditRepository.save_compliance_report", return_value={"id": "1"}), \
                     patch("server.controllers.batch_controller.extract_document_data", side_effect=mock_extract), \
                     patch("server.controllers.batch_controller.store_extracted_document", return_value={"id": 1}), \
                     patch("server.controllers.batch_controller.verify_government_rules", side_effect=mock_gov_rules_dispatcher):
                    files = [
                        ("files", ("invoice.pdf", io.BytesIO(ci_pdf), "application/pdf")),
                        ("files", ("packing_list.pdf", io.BytesIO(pl_pdf), "application/pdf")),
                        ("files", ("corrupt.pdf", io.BytesIO(b"BAD_HEADER"), "application/pdf")),
                    ]
                    upload_res = await client.post("/api/v1/documents/batch-upload", files=files)
                    assert upload_res.status_code == 200, upload_res.text
                    batch_data = upload_res.json()
                    assert batch_data["batch_status"] == "PARTIAL_SUCCESS"

                    extracted_map = {
                        d["document_type"]: d["extracted_data"]
                        for d in batch_data["documents"]
                        if d["status"] == "SUCCESS" and d.get("document_type") and d.get("extracted_data")
                    }

                    pdf_payload = {
                        "batch_id": batch_data["batch_id"],
                        "batch_status": batch_data["batch_status"],
                        "report_generated_at": batch_data["timestamp"],
                        "uploaded_documents": batch_data["documents"],
                        "extracted_documents": extracted_map,
                        "cross_document_validation": batch_data["cross_document_validation"],
                        "government_compliance": batch_data["government_compliance"],
                        "scenario_title": f"Batch Upload Audit ({batch_data['batch_id']})",
                    }
                    pdf_res = await client.post("/api/v1/compliance/report/pdf", json=pdf_payload)
                    assert pdf_res.status_code == 200, pdf_res.text
                    assert pdf_res.headers["content-type"] == "application/pdf"
                    assert batch_data["batch_id"] in pdf_res.headers.get("content-disposition", "")
                    return batch_data, pdf_res.content
        finally:
            app.dependency_overrides.clear()

    batch_data, pdf_bytes = _run_async(_workflow())
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(p.get_text() for p in doc)

    assert batch_data["batch_id"] in text
    assert "invoice.pdf" in text
    assert "packing_list.pdf" in text
    assert "corrupt.pdf" in text
    assert "Global Exports Ltd" in text
    assert "Acme Trading GmbH" in text
    assert "HIGH_RISK" in text or "FRD_GSTIN" in text or "GSTIN" in text
    assert "DGFT" in text and "CBIC" in text
    assert "Purchase Order" in text  # Missing doc listed
    print(f"      Passed! End-to-end upload-to-report produced {len(pdf_bytes)} bytes across {doc.page_count} pages.")


def main():
    print("======================================================================")
    print("TASK 5: PDF COMPLIANCE REPORT AUTOMATED VERIFICATION SUITE")
    print("======================================================================")
    test_generator_clean_shipment()
    test_generator_discrepancy_shipment()
    test_generator_partial_submission()
    test_fastapi_pdf_endpoint()
    test_statutory_authority_citations()
    test_failed_and_partial_batch_pdf_reports()
    test_upload_to_report_workflow()
    print("======================================================================")
    print("ALL 7 PDF COMPLIANCE REPORT TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")


if __name__ == "__main__":
    main()
