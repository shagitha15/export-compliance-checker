"""
Unit test suite for Cross-Document Validation engine.
"""

import json
from services.validation import CrossDocumentValidator, ValidationStatus


def get_mock_documents():
    ci = {
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-10-15",
        "currency": "EUR",
        "total_invoice_amount": 22500.0,
        "subtotal": 22500.0,
        "incoterms": "FOB",
        "exporter_seller": {
            "name": "Global Exports Ltd",
            "country": "India",
            "tax_id_or_gstin": "27AAACG0000A1Z5",
        },
        "consignee_importer": {
            "name": "Acme Trading GmbH",
            "country": "Germany",
        },
        "line_items": [
            {
                "item_no": 1,
                "description": "Precision Machined Steel Components",
                "hs_code": "8483.40",
                "quantity": 500,
                "unit": "PCS",
                "unit_price": 45.0,
                "total_amount": 22500.0,
            }
        ],
    }

    pl = {
        "packing_list_number": "PL-2024-001",
        "invoice_reference_number": "INV-2024-001",
        "exporter_seller": {"name": "Global Exports Limited"},
        "consignee": {"name": "Acme Trading Company"},
        "total_packages_count": 10,
        "total_gross_weight": {"value": 1250.0, "unit": "KG"},
        "total_net_weight": {"value": 1100.0, "unit": "KG"},
        "packages": [
            {
                "package_no": "1-10",
                "description": "Precision Machined Steel Components",
                "quantity": 500,
                "unit": "PCS",
                "net_weight": 1100.0,
                "gross_weight": 1250.0,
            }
        ],
    }

    po = {
        "po_number": "PO-998877",
        "currency": "EUR",
        "total_amount": 25000.0,
        "incoterms": "FOB",
        "buyer": {"name": "Acme Trading GmbH"},
        "vendor_supplier": {"name": "Global Exports Ltd"},
        "line_items": [
            {
                "item_no": 1,
                "description": "Precision Machined Steel Components",
                "quantity": 550,
                "unit_price": 45.0,
                "total_price": 24750.0,
            }
        ],
    }

    sb = {
        "shipping_bill_number": "SB-11223344",
        "shipping_bill_date": "2024-10-18",
        "customs_port_code": "INMAA1",
        "invoice_number": "INV-2024-001",
        "currency": "EUR",
        "total_invoice_value": 22500.0,
        "fob_value": 22500.0,
        "gross_weight": {"value": 1250.5, "unit": "KG"},
        "net_weight": {"value": 1100.0, "unit": "KG"},
        "exporter": {"name": "Global Exports Ltd"},
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
    }

    coo = {
        "certificate_number": "COO-556677",
        "issuing_authority_or_chamber": "Bombay Chamber of Commerce",
        "exporter": {"name": "Global Exports Ltd"},
        "importer_or_consignee": {"name": "Acme Trading GmbH"},
        "origin_criterion": "Wholly Obtained (WO)",
        "item_details": [
            {
                "item_no": 1,
                "hs_code": "8483.40",
                "invoice_number": "INV-2024-001",
                "quantity_or_weight": "500 PCS",
            }
        ],
    }

    return {"Commercial Invoice": ci, "Packing List": pl, "Purchase Order": po, "Shipping Bill": sb, "Certificate of Origin": coo}


def run_tests():
    validator = CrossDocumentValidator()

    # Test 1: Complete Matching Set
    docs = get_mock_documents()
    res1 = validator.validate(docs)
    print("--- Test 1: Complete Matching Document Set ---")
    print(f"Overall Status: {res1.overall_compliance_status}")
    print(f"Summary: {res1.summary.model_dump()}")
    assert res1.overall_compliance_status == ValidationStatus.PASS
    assert res1.summary.failed == 0

    # Test 2: Mismatch Injection (Quantity & Invoice Mismatch)
    print("\n--- Test 2: Discrepancy Injection ---")
    docs_mismatch = get_mock_documents()
    docs_mismatch["Packing List"]["invoice_reference_number"] = "INV-MISMATCH-999"
    docs_mismatch["Packing List"]["packages"][0]["quantity"] = 400
    res2 = validator.validate(docs_mismatch)
    print(f"Overall Status: {res2.overall_compliance_status}")
    print(f"Failed Checks: {res2.summary.failed}")
    for fail in [c for c in res2.cross_document_results if c.status == ValidationStatus.FAIL]:
        print(f"  • [{fail.check_id}] {fail.rule_name}: {fail.message}")
    assert res2.overall_compliance_status == ValidationStatus.FAIL
    assert res2.summary.failed >= 2

    # Test 3: Partial Document Set (Only CI and PL)
    print("\n--- Test 3: Partial Submission (CI + PL only) ---")
    partial_docs = {
        "Commercial Invoice": get_mock_documents()["Commercial Invoice"],
        "Packing List": get_mock_documents()["Packing List"],
    }
    res3 = validator.validate(partial_docs)
    print(f"Overall Status: {res3.overall_compliance_status}")
    print(f"Documents Missing: {res3.documents_missing}")
    print(f"Not Applicable Checks: {res3.summary.not_applicable}")
    assert res3.overall_compliance_status == ValidationStatus.PASS
    assert len(res3.documents_missing) == 3
    assert res3.summary.not_applicable > 0

    print("\n All Cross-Document Validation tests passed successfully!")


if __name__ == "__main__":
    run_tests()
