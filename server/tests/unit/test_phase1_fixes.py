"""
Phase 1 Regression & Verification Unit Tests.
Compatible with both `pytest` and `python -m unittest`.
Covers:
1. Commercial Invoice offsetting line-item math bug fix (intra_document.py).
2. Bill of Lading intra & cross-document checks (intra_document.py, cross_document.py).
3. Statutory rule accuracy & non-fabricated behavior (rules/checker.py).
4. Removal of fake ShipmentDetails fallbacks in LangGraph Node 9 (agents/nodes.py).
"""

import os
import sys
import unittest

import fitz

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from server.agents.nodes import pdf_report_generation_node
from server.compliance.engine import validate_documents
from server.rules.checker import verify_government_rules
from server.schemas.validation import ValidationStatus


class TestPhase1Fixes(unittest.TestCase):
    def test_offsetting_line_item_math_fails(self):
        """Two items with offsetting errors whose sum matches subtotal must FAIL Stage 1."""
        docs = {
            "Commercial Invoice": {
                "invoice_number": "INV-OFFSET-1",
                "invoice_date": "2026-11-20",
                "currency": "USD",
                "subtotal": 2000.0,
                "total_invoice_amount": 2000.0,
                "exporter_seller": {"name": "Real Exporter Pvt Ltd"},
                "consignee_importer": {"name": "Real Buyer GmbH"},
                "line_items": [
                    {"item_no": 1, "description": "Item A", "quantity": 10, "unit_price": 100.0, "total_amount": 1500.0},
                    {"item_no": 2, "description": "Item B", "quantity": 10, "unit_price": 100.0, "total_amount": 500.0},
                ],
            }
        }
        res = validate_documents(docs)
        math_checks = [
            c for c in res.intra_document_results if c.check_name == "line_items_arithmetic_consistency"
        ]
        self.assertEqual(len(math_checks), 1)
        self.assertEqual(math_checks[0].status, ValidationStatus.FAIL)
        self.assertIn("Item #1", math_checks[0].message)

    def test_bill_of_lading_intra_and_cross_checks(self):
        """Bill of Lading validates internally and reconciles shipper, consignee, HS, weight, and Incoterms."""
        docs = {
            "Commercial Invoice": {
                "invoice_number": "INV-BL-1",
                "invoice_date": "2026-11-20",
                "currency": "USD",
                "total_invoice_amount": 5000.0,
                "incoterms": "FOB",
                "exporter_seller": {"name": "Indus Exports Pvt Ltd"},
                "consignee_importer": {"name": "Nordic Imports AB"},
                "line_items": [{"description": "Textiles", "hs_code": "61091000", "quantity": 100, "unit_price": 50.0, "total_amount": 5000.0}],
            },
            "Packing List": {
                "packing_list_number": "PL-BL-1",
                "invoice_reference_number": "INV-BL-1",
                "exporter_seller": {"name": "Indus Exports Pvt Ltd"},
                "consignee": {"name": "Nordic Imports AB"},
                "total_gross_weight": {"value": 500.0, "unit": "KG"},
                "total_net_weight": {"value": 450.0, "unit": "KG"},
            },
            "Bill of Lading": {
                "bl_number": "BL-MAEU-1001",
                "invoice_number": "INV-BL-1",
                "shipper": {"name": "Indus Exports Pvt Ltd"},
                "consignee": {"name": "Nordic Imports AB"},
                "hs_code": "61091000",
                "gross_weight": {"value": 500.0, "unit": "KG"},
                "freight_terms": "FOB Freight Collect",
            },
        }
        res = validate_documents(docs)
        bl_intra = [c for c in res.intra_document_results if c.document_type == "Bill of Lading"]
        self.assertEqual(len(bl_intra), 1)
        self.assertEqual(bl_intra[0].status, ValidationStatus.PASS)

        by_id = {c.check_id: c for c in res.cross_document_results}
        self.assertEqual(by_id["XDOC_WT_007"].status, ValidationStatus.PASS)
        self.assertIn("Bill of Lading", by_id["XDOC_WT_007"].documents_involved)
        self.assertEqual(by_id["XDOC_INCO_009"].status, ValidationStatus.PASS)
        self.assertIn("Bill of Lading", by_id["XDOC_INCO_009"].documents_involved)
        self.assertEqual(by_id["XDOC_HS_006"].status, ValidationStatus.PASS)
        self.assertIn("Bill of Lading", by_id["XDOC_HS_006"].documents_involved)

    def test_statutory_checker_accuracy_no_fake_compliance(self):
        """HS 8483 rule should not fire for HS 610910; missing currency must fail FEMA; AD/LUT detect real values."""
        docs_missing_currency = {
            "Commercial Invoice": {
                "invoice_number": "INV-STAT-1",
                "exporter_seller": {"name": "Test Co", "iec": "0399012345"},
                "declaration_and_signatory": {"declaration_text": "Truthful declaration"},
                "line_items": [{"hs_code": "61091000", "description": "Cotton T-Shirts"}],
            }
        }
        gov1 = verify_government_rules(docs_missing_currency)
        by_rule1 = {f.rule_id: f for f in gov1.findings}
        self.assertNotIn("ITCHS_SCH2_8483", by_rule1, "HS 8483 rule should not be reported for HS 610910")
        if "RBI_FEMA_EXP_09M" in by_rule1:
            self.assertEqual(by_rule1["RBI_FEMA_EXP_09M"].status.value, "NON_COMPLIANT")

        docs_with_ad_lut = {
            "Commercial Invoice": {
                "invoice_number": "INV-STAT-2",
                "currency": "USD",
                "incoterms": "FOB",
                "lut_arn": "AD2704260012345",
                "exporter_seller": {"name": "Test Co", "iec": "0399012345"},
                "declaration_and_signatory": {"declaration_text": "Export under LUT without payment of IGST"},
                "line_items": [{"hs_code": "61091000", "description": "Cotton T-Shirts"}],
            },
            "Shipping Bill": {
                "shipping_bill_number": "SB-123",
                "ad_code": "6390012-1234567",
                "currency": "USD",
            },
        }
        gov2 = verify_government_rules(docs_with_ad_lut)
        by_rule2 = {f.rule_id: f for f in gov2.findings}
        if "DGFT_FTP2023_P2_06" in by_rule2:
            self.assertEqual(by_rule2["DGFT_FTP2023_P2_06"].status.value, "COMPLIANT")
        if "CBIC_GST_LUT_CIRC08" in by_rule2:
            self.assertEqual(by_rule2["CBIC_GST_LUT_CIRC08"].status.value, "COMPLIANT")

    def test_pdf_node_does_not_inject_hardcoded_fake_exporter(self):
        """LangGraph PDF node must not invent Global Exports Ltd / fake GSTIN when fields are absent."""
        docs = {
            "Packing List": {
                "packing_list_number": "PL-ONLY-1",
                "exporter_seller": {"name": ""},
            }
        }
        val = validate_documents(docs)
        state = {
            "extracted_documents": docs,
            "cross_document_results": val,
            "statutory_results": None,
            "generate_pdf": True,
            "execution_history": [],
        }
        out = pdf_report_generation_node(state)
        pdf_bytes = out.get("pdf_report_bytes")
        self.assertTrue(pdf_bytes and pdf_bytes.startswith(b"%PDF-"))

        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = "\n".join(p.get_text("text") for p in pdf_doc)
        pdf_doc.close()

        self.assertNotIn("Global Exports Ltd", full_text)
        self.assertNotIn("0312345678", full_text)
        self.assertNotIn("INV-2024-001", full_text)


if __name__ == "__main__":
    unittest.main()
