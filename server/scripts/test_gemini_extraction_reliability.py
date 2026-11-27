"""
Automated Verification Suite for Gemini Document Extraction Reliability:
1. Successful Gemini extraction (including model capability check & JSON mode).
2. Temporary 503 error recovery with exponential backoff (max 3 retries).
3. Transient 429 & 5xx retry handling.
4. Configurable timeout handling.
5. Retry exhaustion with structured GeminiExtractionError (when fallback disabled or unparseable).
6. Unsupported model rejection without futile retries.
7. Non-silent PyMuPDF text fallback extraction + BatchController resilience.
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import fitz
from google.genai import errors
from httpx import ASGITransport, AsyncClient

from server.document_intelligence.extractor import (
    GeminiExtractionError,
    extract_document_data,
)
from server.integrations.gemini import UnsupportedGeminiModelError, validate_gemini_model
from server.main import app


def _make_api_error(code: int, message: str) -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "message": message}}, None)


def _make_mock_client(generate_side_effect, supported_actions=None):
    if supported_actions is None:
        supported_actions = ["generateContent"]
    client = MagicMock()
    client.models.get.return_value = SimpleNamespace(supported_actions=supported_actions)
    client.models.generate_content.side_effect = generate_side_effect
    return client


def _create_pdf_bytes(title: str, body: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{body}", fontsize=11)
    b = doc.write()
    doc.close()
    return b


def _run_async(coro):
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


class TestGeminiExtractionReliability(unittest.TestCase):
    def test_1_successful_gemini_extraction(self):
        expected_payload = {
            "document_type": "Commercial Invoice",
            "invoice_number": "INV-2024-100",
            "currency": "EUR",
            "total_invoice_amount": 15000.0,
        }
        client = _make_mock_client(
            [SimpleNamespace(text=json.dumps(expected_payload))]
        )

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client):
            result = extract_document_data(
                document_type="Commercial Invoice",
                pdf_text={1: "COMMERCIAL INVOICE\nInvoice No: INV-2024-100\nTotal: 15000 EUR"},
                save_to_disk=False,
            )

        self.assertEqual(result["invoice_number"], "INV-2024-100")
        self.assertEqual(result["total_invoice_amount"], 15000.0)
        self.assertNotIn("_extraction_metadata", result)
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_2_temporary_503_recovers_with_exponential_backoff(self):
        expected_payload = {
            "document_type": "Commercial Invoice",
            "invoice_number": "INV-RETRY-503",
            "currency": "USD",
            "total_invoice_amount": 9800.0,
        }
        client = _make_mock_client(
            [
                _make_api_error(503, "This model is currently experiencing high demand."),
                _make_api_error(503, "This model is currently experiencing high demand."),
                SimpleNamespace(text=json.dumps(expected_payload)),
            ]
        )
        sleep_calls: list[float] = []

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
             patch("server.document_intelligence.extractor.time.sleep", side_effect=sleep_calls.append):
            result = extract_document_data(
                document_type="Commercial Invoice",
                pdf_text={1: "Invoice No: INV-RETRY-503\nTotal: 9800 USD"},
                save_to_disk=False,
                max_retries=3,
                retry_base_delay=0.5,
            )

        self.assertEqual(result["invoice_number"], "INV-RETRY-503")
        self.assertEqual(client.models.generate_content.call_count, 3)
        # Exponential backoff: 0.5 * 2^0 = 0.5, 0.5 * 2^1 = 1.0
        self.assertEqual(sleep_calls, [0.5, 1.0])

    def test_3_transient_429_and_502_retries(self):
        expected_payload = {"document_type": "Packing List", "packing_list_number": "PL-429"}
        client = _make_mock_client(
            [
                _make_api_error(429, "Resource exhausted"),
                _make_api_error(502, "Bad gateway"),
                SimpleNamespace(text=json.dumps(expected_payload)),
            ]
        )
        sleep_calls: list[float] = []

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
             patch("server.document_intelligence.extractor.time.sleep", side_effect=sleep_calls.append):
            result = extract_document_data(
                document_type="Packing List",
                pdf_text={1: "Packing List No: PL-429"},
                save_to_disk=False,
                max_retries=3,
                retry_base_delay=1.0,
            )

        self.assertEqual(result["packing_list_number"], "PL-429")
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_4_retry_exhaustion_max_3_retries_structured_error(self):
        # Request max_retries=10 -> must cap at 3 retries (4 total attempts)
        err_503 = _make_api_error(503, "This model is currently experiencing high demand.")
        client = _make_mock_client([err_503, err_503, err_503, err_503, err_503])
        sleep_calls: list[float] = []

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
             patch("server.document_intelligence.extractor.time.sleep", side_effect=sleep_calls.append):
            with self.assertRaises(GeminiExtractionError) as ctx:
                extract_document_data(
                    document_type="Commercial Invoice",
                    pdf_text={1: "Invoice No: INV-EXHAUST"},
                    save_to_disk=False,
                    max_retries=10,
                    retry_base_delay=0.25,
                    allow_fallback=False,
                )

        exc = ctx.exception
        self.assertEqual(client.models.generate_content.call_count, 4)  # 1 initial + 3 retries
        self.assertEqual(sleep_calls, [0.25, 0.5, 1.0])
        self.assertEqual(exc.status_code, 503)
        self.assertEqual(exc.attempts, 4)
        self.assertTrue(exc.retried)
        self.assertEqual(exc.error_code, "GEMINI_SERVICE_UNAVAILABLE")

    def test_5_configurable_timeout_enforced(self):
        gate = threading.Event()

        def slow_call(**kwargs):
            gate.wait(0.4)
            return SimpleNamespace(text='{"document_type": "Commercial Invoice"}')

        client = _make_mock_client(slow_call)
        sleep_calls: list[float] = []

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
             patch("server.document_intelligence.extractor.time.sleep", side_effect=sleep_calls.append):
            with self.assertRaises(GeminiExtractionError) as ctx:
                extract_document_data(
                    document_type="Commercial Invoice",
                    pdf_text={1: "Some invoice text"},
                    save_to_disk=False,
                    timeout_seconds=0.05,
                    max_retries=1,
                    retry_base_delay=0.01,
                    allow_fallback=False,
                )

        self.assertEqual(ctx.exception.error_code, "GEMINI_TIMEOUT")
        self.assertEqual(ctx.exception.attempts, 2)
        self.assertEqual(sleep_calls, [0.01])

    def test_6_model_capability_validation(self):
        with self.assertRaises(UnsupportedGeminiModelError):
            validate_gemini_model("text-embedding-004")

        mock_client = MagicMock()
        mock_client.models.get.return_value = SimpleNamespace(supported_actions=["embedContent"])
        with self.assertRaises(UnsupportedGeminiModelError):
            validate_gemini_model("gemini-2.5-flash", client=mock_client)

        caps = validate_gemini_model(
            "gemini-2.5-flash",
            client=_make_mock_client([]),
        )
        self.assertTrue(caps["supports_generate_content"])
        self.assertTrue(caps["supports_json_mode"])

    def test_7_pymupdf_fallback_extraction_not_marked_as_ai_success(self):
        err_503 = _make_api_error(503, "This model is currently experiencing high demand.")
        client = _make_mock_client([err_503, err_503, err_503, err_503])

        ci_text = {
            1: (
                "COMMERCIAL INVOICE\n"
                "Invoice No: INV-2024-777\n"
                "Invoice Date: 2024-11-10\n"
                "Exporter: Global Exports Ltd\n"
                "Consignee: Acme Trading GmbH\n"
                "GSTIN: 27AAACG0000A1ZS\n"
                "Currency: EUR\n"
                "Incoterms: FOB\n"
                "HS Code: 848340\n"
                "Quantity: 500\n"
                "Total Invoice Amount: 22500.00\n"
            )
        }

        with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
             patch("server.document_intelligence.extractor.time.sleep"):
            result = extract_document_data(
                document_type="Commercial Invoice",
                pdf_text=ci_text,
                save_to_disk=False,
                max_retries=3,
                retry_base_delay=0.01,
                allow_fallback=True,
            )

        self.assertEqual(result["invoice_number"], "INV-2024-777")
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["total_invoice_amount"], 22500.0)
        self.assertEqual(result["incoterms"], "FOB")
        self.assertEqual(result["exporter_seller"]["tax_id_or_gstin"], "27AAACG0000A1ZS")

        meta = result.get("_extraction_metadata")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["source"], "pymupdf_fallback")
        self.assertFalse(meta["ai_extraction_succeeded"])
        self.assertTrue(meta["fallback_used"])
        self.assertEqual(meta["gemini_status_code"], 503)

    def test_8_batch_resilience_fallback_and_unparseable_failure(self):
        err_503 = _make_api_error(503, "This model is currently experiencing high demand.")
        client = _make_mock_client([err_503] * 10)

        # File 1: real text PDF (fallback extracts structured fields and marks fallback_used=True)
        good_pdf = _create_pdf_bytes(
            "COMMERCIAL INVOICE",
            "Invoice No: INV-2024-888\nExporter: Global Exports Ltd\nCurrency: EUR\nTotal Invoice Amount: 10000\nIncoterms: FOB",
        )
        # File 2: PDF with non-parseable gibberish text -> fallback finds 0 fields -> marked FAILED without crashing batch
        unparseable_pdf = _create_pdf_bytes("COMMERCIAL INVOICE", "~~~ ~~~ ~~~")

        async def _post_batch():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http_client:
                files = [
                    ("files", ("good_invoice.pdf", io.BytesIO(good_pdf), "application/pdf")),
                    ("files", ("unparseable_invoice.pdf", io.BytesIO(unparseable_pdf), "application/pdf")),
                ]
                return await http_client.post("/api/v1/documents/batch-upload", files=files)

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
        try:
            with patch("server.document_intelligence.extractor.get_gemini_client", return_value=client), \
                 patch("server.document_intelligence.extractor.time.sleep"), \
                 patch("server.auth.dependencies.OrganizationRepository.list_user_organizations", return_value=test_membership), \
                 patch("server.storage.document_storage.DocumentStorageService.upload_private_pdf", return_value="org/batch/doc.pdf"), \
                 patch("server.repositories.audit_repository.AuditRepository.save_batch_audit", return_value={"id": "1"}), \
                 patch("server.controllers.batch_controller.store_extracted_document", return_value={"id": 1}), \
                 patch("server.controllers.batch_controller.verify_government_rules", return_value=None):
                res = _run_async(_post_batch())
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["batch_status"], "PARTIAL_SUCCESS")
        self.assertEqual(body["summary"]["successful_count"], 1)
        self.assertEqual(body["summary"]["failed_count"], 1)

        doc1, doc2 = body["documents"]
        self.assertEqual(doc1["status"], "SUCCESS")
        self.assertTrue(doc1["fallback_used"])
        self.assertEqual(doc1["extraction_method"], "pymupdf_fallback")
        self.assertEqual(doc1["error_code"], "GEMINI_EXTRACTION_FALLBACK")
        self.assertIn("PyMuPDF text fallback", doc1["warning"])

        self.assertEqual(doc2["status"], "FAILED")
        self.assertEqual(doc2["error_code"], "GEMINI_SERVICE_UNAVAILABLE")
        self.assertIn("503", doc2["error"])


if __name__ == "__main__":
    print("=" * 80)
    print("GEMINI DOCUMENT EXTRACTION RELIABILITY TEST SUITE")
    print("=" * 80)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGeminiExtractionReliability)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
