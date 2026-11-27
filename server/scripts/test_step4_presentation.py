"""
Step 4 Presentation Layer Verification Runner.
Tests Controllers, Routers, OpenAPI Route Bindings, and ASGI HTTP Endpoints.
"""

import asyncio
import io
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from test_validation import get_mock_documents

def build_valid_docs():
    docs = get_mock_documents()
    docs["Commercial Invoice"]["exporter_iec"] = "0512345678"
    docs["Commercial Invoice"]["lut_arn"] = "AD060324001234A"
    docs["Shipping Bill"]["section_50_declaration"] = True
    return docs



async def run_presentation_tests():
    print("=" * 80)
    print("  STEP 4 PRESENTATION LAYER VERIFICATION SUITE")
    print("=" * 80)

    # 1. Imports and App Factory Check
    print("\n[CHECK 1] Testing Application Factory and Route Registry...")
    from server.main import app, create_application
    from server.controllers.document_controller import DocumentController
    from server.controllers.compliance_controller import ComplianceController
    from server.schemas.upload import DocumentType
    from server.schemas.validation import ValidationDirectPayload, ValidateStoredFilesPayload

    assert app is not None, "app must not be None"

    # Inspect registered route paths via OpenAPI schema
    openapi_schema = app.openapi()
    route_paths = list(openapi_schema.get("paths", {}).keys())
    expected_paths = [
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
    for expected in expected_paths:
        assert expected in route_paths, f"Missing registered route: {expected}"
    print(f"  PASS: All {len(expected_paths)} expected v1 API routes correctly registered in FastAPI app.")

    # 2. Controller Direct Unit Tests
    print("\n[CHECK 2] Testing ComplianceController Unit Logic...")
    valid_docs = build_valid_docs()
    # 2A. Direct Validation
    payload = ValidationDirectPayload(documents=valid_docs)
    val_report = await ComplianceController.validate_documents(payload)
    assert val_report.overall_compliance_status.value == "PASS", f"Expected PASS, got {val_report.overall_compliance_status}"
    assert val_report.summary.passed == 16, f"Expected 16 passed checks, got {val_report.summary.passed}"
    print("  PASS: ComplianceController.validate_documents executed 16/16 checks cleanly.")

    # 2B. Validation with Discrepancy
    discrepant_docs = json.loads(json.dumps(valid_docs))
    discrepant_docs["Packing List"]["invoice_reference_number"] = "INV-MISMATCH"
    payload_discrepant = ValidationDirectPayload(documents=discrepant_docs)
    val_fail_report = await ComplianceController.validate_documents(payload_discrepant)
    assert val_fail_report.overall_compliance_status.value == "FAIL"
    assert val_fail_report.summary.failed >= 1
    print("  PASS: ComplianceController.validate_documents correctly detected discrepancy (FAIL).")


    # 2C. Empty documents error check
    try:
        await ComplianceController.validate_documents(ValidationDirectPayload(documents={}))
        assert False, "Should have raised HTTPException 400"
    except HTTPException as exc:
        assert exc.status_code == 400
        print("  PASS: ComplianceController correctly raised 400 on empty documents payload.")

    # 2D. Statutory Verification
    gov_report = await ComplianceController.verify_statutory_rules(payload)
    assert gov_report.summary.total_rules_evaluated > 0
    print(f"  PASS: ComplianceController.verify_statutory_rules evaluated {gov_report.summary.total_rules_evaluated} provisions.")

    # 2E. Unified Audit
    audit_report = await ComplianceController.audit_full_shipment(payload)
    assert audit_report.cross_document_validation.summary.total_checks == 16
    assert audit_report.government_compliance.summary.total_rules_evaluated > 0
    print("  PASS: ComplianceController.audit_full_shipment executed unified audit.")

    # 3. Controller Direct Document Validation Checks
    print("\n[CHECK 3] Testing DocumentController Input Validations...")
    # Test non-existent saved file check
    try:
        await DocumentController.extract_saved_document("non_existent_file_xyz_123.pdf", DocumentType.COMMERCIAL_INVOICE)
        assert False, "Should have raised HTTPException 404"
    except HTTPException as exc:
        assert exc.status_code == 404
        print("  PASS: DocumentController correctly raised 404 for non-existent saved document.")

    # 4. HTTP End-to-End Async Client Smoke Tests
    print("\n[CHECK 4] Testing HTTP Endpoints via ASGITransport...")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 4A. Root welcome route
        res = await client.get("/")
        assert res.status_code == 200, f"Root returned {res.status_code}"
        assert res.json()["version"] == "1.0.0"
        print("  PASS: GET / -> 200 OK")

        # 4B. Health check route
        res = await client.get("/api/v1/health")
        assert res.status_code == 200, f"Health returned {res.status_code}"
        assert res.json()["success"] is True
        print("  PASS: GET /api/v1/health -> 200 OK")

        # 4C. POST /api/v1/compliance/validate
        res = await client.post("/api/v1/compliance/validate", json={"documents": valid_docs})
        assert res.status_code == 200, f"Validate returned {res.status_code}: {res.text}"
        data = res.json()
        assert data["overall_compliance_status"] == "PASS"
        assert data["summary"]["passed"] == 16
        print("  PASS: POST /api/v1/compliance/validate -> 200 OK (16 passed checks)")

        # 4D. POST /api/v1/compliance/verify-rules
        res = await client.post("/api/v1/compliance/verify-rules", json={"documents": valid_docs})
        assert res.status_code == 200, f"Verify rules returned {res.status_code}: {res.text}"
        gov_data = res.json()
        assert "overall_government_compliance" in gov_data
        print(f"  PASS: POST /api/v1/compliance/verify-rules -> 200 OK (status: {gov_data['overall_government_compliance']})")

        # 4E. POST /api/v1/compliance/verify-government-rules (alias)
        res = await client.post("/api/v1/compliance/verify-government-rules", json={"documents": valid_docs})
        assert res.status_code == 200, f"Verify rules alias returned {res.status_code}: {res.text}"
        print("  PASS: POST /api/v1/compliance/verify-government-rules (alias) -> 200 OK")

        # 4F. POST /api/v1/compliance/audit
        res = await client.post("/api/v1/compliance/audit", json={"documents": valid_docs})
        assert res.status_code == 200, f"Audit returned {res.status_code}: {res.text}"
        audit_data = res.json()
        assert "cross_document_validation" in audit_data
        assert "government_compliance" in audit_data
        print("  PASS: POST /api/v1/compliance/audit -> 200 OK (Unified Audit)")


        # 4G. POST /api/v1/compliance/validate with bad payload (400 validation error)
        res = await client.post("/api/v1/compliance/validate", json={"documents": {}})
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        print("  PASS: POST /api/v1/compliance/validate (empty documents) -> 400 Bad Request")

        # 4H. POST /api/v1/documents/upload with non-PDF byte header (400 rejection)
        files = {"file": ("test.pdf", io.BytesIO(b"NOT_A_PDF_HEADER"), "application/pdf")}
        data = {"document_type": "Commercial Invoice"}
        res = await client.post("/api/v1/documents/upload", files=files, data=data)
        assert res.status_code == 400, f"Expected 400 for corrupt PDF header, got {res.status_code}: {res.text}"
        assert "missing %PDF signature" in res.json().get("detail", "")
        print("  PASS: POST /api/v1/documents/upload (corrupt header) -> 400 Bad Request")

        # 4I. POST /api/v1/documents/extract-saved/{non_existent} -> 404
        res = await client.post("/api/v1/documents/extract-saved/missing_doc_9999.pdf?document_type=Commercial Invoice")
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        print("  PASS: POST /api/v1/documents/extract-saved/missing.pdf -> 404 Not Found")

    print("\n" + "=" * 80)
    print("  ALL STEP 4 PRESENTATION LAYER TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_presentation_tests())
