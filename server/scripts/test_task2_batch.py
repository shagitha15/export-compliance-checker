"""
Task 2 Batch API Verification Runner.
Validates all requirements for the 5-Document Batch API:
- 1 valid document
- 5 valid documents
- >5 documents rejection
- Unsupported file formats
- Corrupted PDFs
- Empty files
- Duplicate documents (name & content)
- Partial processing failures
- Existing endpoint preservation
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


def create_pdf(title: str, body: str) -> bytes:
    """Creates a valid PDF stream in memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{body}", fontsize=11)
    b = doc.write()
    doc.close()
    return b


async def run_batch_tests():
    print("=" * 80)
    print("  TASK 2: 5-DOCUMENT BATCH API TEST SUITE")
    print("=" * 80)

    from server.auth.dependencies import get_current_user
    from server.auth.models import AuthenticatedUser, OrgRole
    from server.main import app
    from server.schemas.batch import BatchProcessingStatus, DocumentItemStatus

    test_user = AuthenticatedUser(user_id="test-uid", email="test@example.com")
    test_membership = [{
        "organization_id": "11111111-1111-4111-8111-111111111111",
        "user_id": "test-uid",
        "role": OrgRole.ADMIN.value,
        "status": "active",
        "organization": {"id": "11111111-1111-4111-8111-111111111111", "name": "Test Org"},
    }]
    app.dependency_overrides[get_current_user] = lambda: test_user

    transport = ASGITransport(app=app)
    p1 = patch("server.auth.dependencies.OrganizationRepository.list_user_organizations", return_value=test_membership)
    p2 = patch("server.storage.document_storage.DocumentStorageService.upload_private_pdf", return_value="org/batch/doc.pdf")
    p3 = patch("server.repositories.audit_repository.AuditRepository.save_batch_audit", return_value={"id": "1"})
    p1.start()
    p2.start()
    p3.start()
    try:
      async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        # ----------------------------------------------------------------------
        # TEST 1: Route Registration
        # ----------------------------------------------------------------------
        print("\n[TEST 1] Verifying OpenAPI Route Registration...")
        openapi = app.openapi()
        paths = list(openapi.get("paths", {}).keys())
        assert "/api/v1/documents/batch-upload" in paths, "Missing /api/v1/documents/batch-upload"
        print("  PASS: /api/v1/documents/batch-upload registered in OpenAPI paths.")

        # ----------------------------------------------------------------------
        # TEST 2: Upload One Valid Document
        # ----------------------------------------------------------------------
        print("\n[TEST 2] Testing Batch with 1 Valid Document...")
        pdf1 = create_pdf("COMMERCIAL INVOICE", "Invoice No: INV-2024-001\nExporter: Global Exports Ltd\nTotal: 22500 EUR")
        mock_docs = get_mock_documents()
        ci_mock = mock_docs["Commercial Invoice"]

        def mock_extract_dispatcher(*args, **kwargs):
            doc_type = kwargs.get("document_type") or (args[0] if args else "Commercial Invoice")
            return mock_docs.get(doc_type, ci_mock)


        with patch("server.controllers.batch_controller.extract_document_data", side_effect=mock_extract_dispatcher):
            files = [
                ("files", ("invoice.pdf", io.BytesIO(pdf1), "application/pdf")),
            ]
            res = await client.post("/api/v1/documents/batch-upload", files=files)
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["batch_status"] == "SUCCESS"
            assert data["summary"]["total_files_received"] == 1
            assert data["summary"]["successful_count"] == 1
            assert data["summary"]["failed_count"] == 0
            assert len(data["documents"]) == 1
            assert data["documents"][0]["status"] == "SUCCESS"
            assert data["documents"][0]["document_type"] == "Commercial Invoice"
            assert data["cross_document_validation"] is not None
            assert len(data["cross_document_validation"]["documents_missing"]) == 4
            print("  PASS: Single valid document processed with SUCCESS and partial cross-doc validation.")

        # ----------------------------------------------------------------------
        # TEST 3: Upload Five Valid Documents (Full Set)
        # ----------------------------------------------------------------------
        print("\n[TEST 3] Testing Batch with 5 Valid Documents (Complete Trade Set)...")
        pdf_ci = create_pdf("COMMERCIAL INVOICE", "Invoice No: INV-2024-001\nLUT ARN: AD060324001234A\nTotal: 22500 EUR")
        pdf_pl = create_pdf("PACKING LIST", "Packing List No: PL-2024-001\nTotal Packages: 10\nGross Wt: 1250 KG")
        pdf_po = create_pdf("PURCHASE ORDER", "Purchase Order No: PO-998877\nVendor: Global Exports Ltd\nTotal: 25000 EUR")
        pdf_sb = create_pdf("SHIPPING BILL", "Shipping Bill No: SB-11223344\nCustoms Port: INMAA1\nSection 50 Declaration")
        pdf_coo = create_pdf("CERTIFICATE OF ORIGIN", "Certificate No: COO-556677\nChamber of Commerce\nOrigin Criterion: WO")

        with patch("server.controllers.batch_controller.extract_document_data", side_effect=mock_extract_dispatcher):
            files = [
                ("files", ("commercial_invoice.pdf", io.BytesIO(pdf_ci), "application/pdf")),
                ("files", ("packing_list.pdf", io.BytesIO(pdf_pl), "application/pdf")),
                ("files", ("purchase_order.pdf", io.BytesIO(pdf_po), "application/pdf")),
                ("files", ("shipping_bill.pdf", io.BytesIO(pdf_sb), "application/pdf")),
                ("files", ("certificate_of_origin.pdf", io.BytesIO(pdf_coo), "application/pdf")),
            ]
            res = await client.post("/api/v1/documents/batch-upload", files=files)
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["batch_status"] == "SUCCESS"
            assert data["summary"]["total_files_received"] == 5
            assert data["summary"]["successful_count"] == 5
            assert data["summary"]["failed_count"] == 0
            assert len(data["summary"]["detected_document_types"]) == 5
            assert len(data["summary"]["missing_document_types"]) == 0
            assert data["cross_document_validation"]["overall_compliance_status"] == "PASS"
            assert data["cross_document_validation"]["summary"]["passed"] == 16
            print(f"  PASS: 5 valid documents processed with SUCCESS; all 16 cross-document checks passed.")

        # ----------------------------------------------------------------------
        # TEST 4: Upload More Than Five Documents (>5 Rejection)
        # ----------------------------------------------------------------------
        print("\n[TEST 4] Testing Batch Size Limit Rejection (>5 Documents)...")
        files_overflow = [
            ("files", (f"doc_{i}.pdf", io.BytesIO(create_pdf("INVOICE", f"Doc {i}")), "application/pdf"))
            for i in range(6)
        ]
        res = await client.post("/api/v1/documents/batch-upload", files=files_overflow)
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
        assert "Batch upload limit exceeded: Maximum 5 documents allowed" in res.json().get("detail", "")
        print("  PASS: Batch of 6 documents rejected with 400 Bad Request.")

        # ----------------------------------------------------------------------
        # TEST 5: Upload Unsupported File Formats
        # ----------------------------------------------------------------------
        print("\n[TEST 5] Testing Unsupported File Formats...")
        files_invalid_ext = [
            ("files", ("spreadsheet.xlsx", io.BytesIO(b"NOT_A_PDF_CONTENT"), "application/vnd.ms-excel")),
        ]
        res = await client.post("/api/v1/documents/batch-upload", files=files_invalid_ext)
        assert res.status_code == 200
        data = res.json()
        assert data["batch_status"] == "FAILED"
        assert data["documents"][0]["status"] == "FAILED"
        assert data["documents"][0]["error_code"] == "INVALID_EXTENSION"
        print("  PASS: Unsupported .xlsx extension flagged as FAILED with INVALID_EXTENSION.")

        # ----------------------------------------------------------------------
        # TEST 6: Upload Corrupted PDFs
        # ----------------------------------------------------------------------
        print("\n[TEST 6] Testing Corrupted PDF Header Rejection...")
        files_corrupt = [
            ("files", ("corrupted_invoice.pdf", io.BytesIO(b"MALFORMED_HEADER_NOT_PDF"), "application/pdf")),
        ]
        res = await client.post("/api/v1/documents/batch-upload", files=files_corrupt)
        assert res.status_code == 200
        data = res.json()
        assert data["batch_status"] == "FAILED"
        assert data["documents"][0]["status"] == "FAILED"
        assert data["documents"][0]["error_code"] == "CORRUPT_PDF_HEADER"
        print("  PASS: Corrupted PDF header flagged as FAILED with CORRUPT_PDF_HEADER.")

        # ----------------------------------------------------------------------
        # TEST 7: Upload Empty Files (0 Bytes)
        # ----------------------------------------------------------------------
        print("\n[TEST 7] Testing Empty File (0 Bytes) Rejection...")
        files_empty = [
            ("files", ("empty_doc.pdf", io.BytesIO(b""), "application/pdf")),
        ]
        res = await client.post("/api/v1/documents/batch-upload", files=files_empty)
        assert res.status_code == 200
        data = res.json()
        assert data["batch_status"] == "FAILED"
        assert data["documents"][0]["status"] == "FAILED"
        assert data["documents"][0]["error_code"] == "EMPTY_FILE"
        print("  PASS: Empty file (0 bytes) flagged as FAILED with EMPTY_FILE.")

        # ----------------------------------------------------------------------
        # TEST 8: Upload Duplicate Documents
        # ----------------------------------------------------------------------
        print("\n[TEST 8] Testing Duplicate Document Detection...")
        duplicate_pdf_bytes = create_pdf("COMMERCIAL INVOICE", "Invoice INV-DUP-1")
        with patch("server.controllers.batch_controller.extract_document_data", side_effect=mock_extract_dispatcher):
            # 8A: Identical filename duplicate
            files_dup_name = [
                ("files", ("duplicate.pdf", io.BytesIO(duplicate_pdf_bytes), "application/pdf")),
                ("files", ("duplicate.pdf", io.BytesIO(duplicate_pdf_bytes), "application/pdf")),
            ]
            res = await client.post("/api/v1/documents/batch-upload", files=files_dup_name)
            assert res.status_code == 200
            data = res.json()
            assert data["summary"]["successful_count"] == 1
            assert data["summary"]["duplicate_count"] == 1
            assert data["documents"][0]["status"] == "SUCCESS"
            assert data["documents"][1]["status"] == "DUPLICATE"
            print("  PASS: Duplicate filename correctly flagged as DUPLICATE without failing batch.")

            # 8B: Different filename but identical content duplicate
            files_dup_content = [
                ("files", ("original.pdf", io.BytesIO(duplicate_pdf_bytes), "application/pdf")),
                ("files", ("copy_of_original.pdf", io.BytesIO(duplicate_pdf_bytes), "application/pdf")),
            ]
            res = await client.post("/api/v1/documents/batch-upload", files=files_dup_content)
            assert res.status_code == 200
            data = res.json()
            assert data["summary"]["duplicate_count"] == 1
            assert data["documents"][1]["status"] == "DUPLICATE"
            assert data["documents"][1]["error_code"] == "DUPLICATE_CONTENT"
            print("  PASS: Duplicate content hash (SHA-256) correctly detected and flagged as DUPLICATE.")

        # ----------------------------------------------------------------------
        # TEST 9: Partial Processing Failures (Resilience)
        # ----------------------------------------------------------------------
        print("\n[TEST 9] Testing Partial Processing Failures (Mixed Batch of 5 Files)...")
        # 2 good files, 3 bad files (1 corrupt, 1 empty, 1 bad extension)
        good_ci = create_pdf("COMMERCIAL INVOICE", "Invoice No: INV-2024-001\nTotal: 22500 EUR")
        good_pl = create_pdf("PACKING LIST", "Packing List No: PL-2024-001\nTotal Gross Weight: 1250 KG")

        with patch("server.controllers.batch_controller.extract_document_data", side_effect=mock_extract_dispatcher):
            files_mixed = [
                ("files", ("valid_invoice.pdf", io.BytesIO(good_ci), "application/pdf")),
                ("files", ("corrupt_file.pdf", io.BytesIO(b"NOT_A_PDF"), "application/pdf")),
                ("files", ("valid_packing.pdf", io.BytesIO(good_pl), "application/pdf")),
                ("files", ("empty_file.pdf", io.BytesIO(b""), "application/pdf")),
                ("files", ("wrong_ext.txt", io.BytesIO(b"plain text"), "text/plain")),
            ]
            res = await client.post("/api/v1/documents/batch-upload", files=files_mixed)
            assert res.status_code == 200, f"Expected 200, got {res.status_code}"
            data = res.json()
            assert data["batch_status"] == "PARTIAL_SUCCESS"
            assert data["summary"]["total_files_received"] == 5
            assert data["summary"]["successful_count"] == 2
            assert data["summary"]["failed_count"] == 3
            assert data["summary"]["duplicate_count"] == 0
            # Confirm cross-document validation ran on the 2 successful docs
            assert data["cross_document_validation"] is not None
            assert data["cross_document_validation"]["overall_compliance_status"] == "PASS"
            print("  PASS: Partial failure batch handled resiliently (batch_status=PARTIAL_SUCCESS, 2 passed, 3 failed).")

        # ----------------------------------------------------------------------
        # TEST 10: Existing API Functionality Unaffected
        # ----------------------------------------------------------------------
        print("\n[TEST 10] Verifying Existing API Functionality Remains Unaffected...")
        # 10A: GET /api/v1/health
        h = await client.get("/api/v1/health")
        assert h.status_code == 200

        # 10B: POST /api/v1/compliance/validate
        v = await client.post("/api/v1/compliance/validate", json={"documents": mock_docs})
        assert v.status_code == 200
        assert v.json()["overall_compliance_status"] == "PASS"

        # 10C: POST /api/v1/compliance/verify-rules
        r = await client.post("/api/v1/compliance/verify-rules", json={"documents": mock_docs})
        assert r.status_code == 200

        # 10D: POST /api/v1/compliance/audit
        a = await client.post("/api/v1/compliance/audit", json={"documents": mock_docs})
        assert a.status_code == 200

        print("  PASS: All existing routes (/health, /validate, /verify-rules, /audit) remain 100% operational.")
    finally:
        p3.stop()
        p2.stop()
        p1.stop()
        app.dependency_overrides.clear()

    print("\n" + "=" * 80)
    print("  ALL TASK 2 BATCH API TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 80)


if __name__ == "__main__":
    if sys.platform == "win32":
        import _overlapped

        class _InProcessProactorEventLoop(asyncio.ProactorEventLoop):
            """Windows ProactorEventLoop using IOCP wakeups instead of TCP socketpair().

            Standard BaseProactorEventLoop._make_self_pipe() calls socket.socketpair(),
            which binds 127.0.0.1 and blocks indefinitely in accept() when loopback TCP
            connections are restricted. Using PostQueuedCompletionStatus avoids sockets
            entirely for in-memory ASGI tests.
            """

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
                    _overlapped.PostQueuedCompletionStatus(self._proactor._iocp, 0, 0, self._wakeup_ov.address)

        asyncio.run(run_batch_tests(), loop_factory=_InProcessProactorEventLoop)
    else:
        asyncio.run(run_batch_tests())
