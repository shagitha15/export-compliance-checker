"""
Task 3 Live Batch Upload Integration Verification Suite.
Tests the real Batch Ingestion API controller with actual sample PDF binaries:
- 1 valid document
- 5 valid documents (complete trade set)
- Rejection of >5 documents
- Duplicate document handling
- Corrupted PDF handling (CORRUPT_PDF_STRUCTURE)
- Partial success handling (mix of valid and corrupted documents)
- Verifies BatchUploadResponse schema compliance
"""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path
from unittest.mock import patch

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz  # PyMuPDF
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from server.controllers.batch_controller import BatchController
from server.schemas.batch import BatchProcessingStatus, BatchUploadResponse, DocumentItemStatus
from test_validation import get_mock_documents


def create_sample_pdf(title: str, body: str) -> bytes:
    """Creates a real valid PDF document using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{body}", fontsize=11)
    b = doc.write()
    doc.close()
    return b


def get_mock_extractor():
    mock_docs = get_mock_documents()
    # Add shipping bill weights in dict format expected by cross_document engine
    if "Shipping Bill" in mock_docs:
        mock_docs["Shipping Bill"]["gross_weight"] = {"value": 1250.0, "unit": "KG"}
        mock_docs["Shipping Bill"]["net_weight"] = {"value": 1100.0, "unit": "KG"}
    if "Packing List" in mock_docs:
        mock_docs["Packing List"]["exporter_seller"] = {"name": "Global Exports Ltd"}
    if "Certificate of Origin" in mock_docs:
        mock_docs["Certificate of Origin"]["issuing_authority_or_chamber"] = "Bombay Chamber of Commerce"

    def extractor(*args, **kwargs):
        doc_type = kwargs.get("document_type") or (args[0] if args else "Commercial Invoice")
        return mock_docs.get(doc_type, mock_docs["Commercial Invoice"])

    return extractor


async def run_live_batch_tests():
    print("=" * 80)
    print("  TASK 3: LIVE BATCH UPLOAD INTEGRATION TEST SUITE (ACTUAL PDF BINARIES)")
    print("=" * 80)

    extractor = get_mock_extractor()
    passed = 0
    total = 0

    def assert_test(cond: bool, msg: str):
        nonlocal passed, total
        total += 1
        assert cond, f"FAILED: {msg}"
        print(f"  [PASS] Test {total}: {msg}")
        passed += 1

    with patch("server.controllers.batch_controller.extract_document_data", side_effect=extractor):
        # ------------------------------------------------------------------
        # TEST 1: Single Valid Document Batch
        # ------------------------------------------------------------------
        print("\n[STAGE 1] Testing Batch Ingestion with 1 Valid PDF Binary...")
        ci_pdf = create_sample_pdf(
            "COMMERCIAL INVOICE",
            "Invoice No: INV-2024-001\nExporter: Global Exports Ltd\nTotal: 22500 EUR"
        )
        file1 = UploadFile(
            filename="commercial_invoice.pdf",
            file=io.BytesIO(ci_pdf),
            headers={"content-type": "application/pdf"}
        )
        res1 = await BatchController.process_batch_upload([file1], ["Commercial Invoice"])
        assert_test(isinstance(res1, BatchUploadResponse), "Response is valid BatchUploadResponse instance")
        assert_test(res1.batch_status == BatchProcessingStatus.SUCCESS, "Batch status is SUCCESS")
        assert_test(res1.summary.total_files_received == 1, "Total files received is 1")
        assert_test(res1.summary.successful_count == 1, "Successful count is 1")
        assert_test(res1.documents[0].status == DocumentItemStatus.SUCCESS, "Document item status is SUCCESS")
        assert_test(res1.cross_document_validation is not None, "Cross-document validation was executed")
        assert_test(len(res1.cross_document_validation.documents_missing) == 4, "Correctly detected 4 missing document types")

        # ------------------------------------------------------------------
        # TEST 2: Complete 5-Document Batch (Full Trade Set)
        # ------------------------------------------------------------------
        print("\n[STAGE 2] Testing Complete 5-Document Batch (Real PDF Binaries)...")
        pl_pdf = create_sample_pdf("PACKING LIST", "PL No: PL-2024-001\nPackages: 10\nGross: 1250 KG")
        po_pdf = create_sample_pdf("PURCHASE ORDER", "PO No: PO-998877\nTotal: 22500 EUR")
        sb_pdf = create_sample_pdf("SHIPPING BILL", "SB No: SB-11223344\nPort: INMAA1\nTotal: 22500 EUR")
        coo_pdf = create_sample_pdf("CERTIFICATE OF ORIGIN", "COO No: COO-556677\nOrigin: WO")

        files5 = [
            UploadFile(filename="Commercial_Invoice.pdf", file=io.BytesIO(ci_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="Packing_List.pdf", file=io.BytesIO(pl_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="Purchase_Order.pdf", file=io.BytesIO(po_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="Shipping_Bill.pdf", file=io.BytesIO(sb_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="Certificate_of_Origin.pdf", file=io.BytesIO(coo_pdf), headers={"content-type": "application/pdf"}),
        ]
        types5 = [
            "Commercial Invoice",
            "Packing List",
            "Purchase Order",
            "Shipping Bill",
            "Certificate of Origin",
        ]
        res5 = await BatchController.process_batch_upload(files5, types5)
        assert_test(res5.batch_status == BatchProcessingStatus.SUCCESS, "Full 5-document batch status is SUCCESS")
        assert_test(res5.summary.total_files_received == 5, "Received exactly 5 files")
        assert_test(res5.summary.successful_count == 5, "All 5 documents successfully parsed")
        assert_test(len(res5.summary.missing_document_types) == 0, "Zero missing document types in complete trade set")
        assert_test(res5.cross_document_validation is not None, "Full cross-document reconciliation report present")
        assert_test(res5.cross_document_validation.summary.total_checks == 16, "All 16 cross-document rules evaluated")
        assert_test(res5.government_compliance is not None, "Statutory Indian export compliance audit present")

        # ------------------------------------------------------------------
        # TEST 3: Batch Limit Enforcement (>5 Files Rejected)
        # ------------------------------------------------------------------
        print("\n[STAGE 3] Testing Batch Limit Enforcement (>5 Files)...")
        files6 = [
            UploadFile(filename=f"doc_{i}.pdf", file=io.BytesIO(ci_pdf), headers={"content-type": "application/pdf"})
            for i in range(6)
        ]
        try:
            await BatchController.process_batch_upload(files6)
            assert False, "Should have thrown 400 Bad Request for >5 files"
        except HTTPException as exc:
            assert_test(exc.status_code == 400, "Rejected with HTTP 400 Bad Request")
            assert_test("Batch upload limit exceeded" in exc.detail, "Error detail explains max 5 files limit")

        # ------------------------------------------------------------------
        # TEST 4: Duplicate Filename Detection in Same Batch
        # ------------------------------------------------------------------
        print("\n[STAGE 4] Testing Duplicate Filename Detection...")
        dup_files = [
            UploadFile(filename="invoice.pdf", file=io.BytesIO(ci_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="invoice.pdf", file=io.BytesIO(ci_pdf), headers={"content-type": "application/pdf"}),
        ]
        res_dup = await BatchController.process_batch_upload(dup_files)
        assert_test(res_dup.summary.duplicate_count == 1, "Detected duplicate document in queue")
        assert_test(res_dup.documents[1].status == DocumentItemStatus.DUPLICATE, "Duplicate item flagged with DUPLICATE status")

        # ------------------------------------------------------------------
        # TEST 5: Corrupted PDF Structure Handling
        # ------------------------------------------------------------------
        print("\n[STAGE 5] Testing Corrupted PDF Structure Handling...")
        corrupt_bytes = b"%PDF-1.4\nCorrupted binary junk that cannot be parsed as valid PDF object tree"
        corrupt_file = UploadFile(filename="corrupted.pdf", file=io.BytesIO(corrupt_bytes), headers={"content-type": "application/pdf"})
        res_corrupt = await BatchController.process_batch_upload([corrupt_file])
        assert_test(res_corrupt.batch_status == BatchProcessingStatus.FAILED, "Corrupted batch status is FAILED")
        assert_test(res_corrupt.documents[0].status == DocumentItemStatus.FAILED, "Corrupted document flagged as FAILED")
        assert_test(res_corrupt.documents[0].error_code == "CORRUPT_PDF_STRUCTURE", "Flagged with error_code CORRUPT_PDF_STRUCTURE")

        # ------------------------------------------------------------------
        # TEST 6: Partial Processing Failure Tolerance
        # ------------------------------------------------------------------
        print("\n[STAGE 6] Testing Partial Processing Failure Tolerance...")
        mixed_files = [
            UploadFile(filename="good_invoice.pdf", file=io.BytesIO(ci_pdf), headers={"content-type": "application/pdf"}),
            UploadFile(filename="bad_corrupt.pdf", file=io.BytesIO(corrupt_bytes), headers={"content-type": "application/pdf"}),
        ]
        res_mixed = await BatchController.process_batch_upload(mixed_files, ["Commercial Invoice", None])
        assert_test(res_mixed.batch_status == BatchProcessingStatus.PARTIAL_SUCCESS, "Mixed batch returns PARTIAL_SUCCESS")
        assert_test(res_mixed.summary.successful_count == 1, "1 valid file parsed successfully")
        assert_test(res_mixed.summary.failed_count == 1, "1 corrupt file isolated without crashing batch")
        assert_test(res_mixed.cross_document_validation is not None, "Valid document processed through compliance engine")

    print("\n" + "=" * 80)
    print(f"  ALL {total} LIVE BATCH UPLOAD TESTS PASSED SUCCESSFULLY! ({passed}/{total})")
    print("=" * 80)


if __name__ == "__main__":
    if sys.platform == "win32":
        import _overlapped

        class _InProcessProactorEventLoop(asyncio.ProactorEventLoop):
            """IOCP-based Windows event loop avoiding TCP socketpair() in restricted sandboxes."""

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

        asyncio.run(run_live_batch_tests(), loop_factory=_InProcessProactorEventLoop)
    else:
        asyncio.run(run_live_batch_tests())
