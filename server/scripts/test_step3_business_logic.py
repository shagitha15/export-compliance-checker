"""
Verification test suite for Step 3 (Core Business Logic Migration).
Tests server.ocr, server.document_intelligence, server.compliance, and server.rules in isolation.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    print("================================================================================")
    print("  STEP 3 CORE BUSINESS LOGIC VERIFICATION SUITE")
    print("================================================================================")

    # 1. Test server.ocr
    print("\n[CHECK 1] Testing server.ocr...")
    from server.ocr import extract_text_from_pdf

    sample_pdf = PROJECT_ROOT / "uploads" / "bilexor-commercial-invoice-template_78ddd12ab7.pdf"
    if sample_pdf.is_file():
        extracted = extract_text_from_pdf(sample_pdf)
        assert len(extracted) > 0, "OCR should extract at least 1 page"
        print(f"  PASS: server.ocr extracted text from {len(extracted)} page(s) successfully.")
    else:
        print("  NOTICE: Sample PDF not found; skipped text stream read check.")

    # 2. Test server.document_intelligence
    print("\n[CHECK 2] Testing server.document_intelligence...")
    from server.document_intelligence import (
        DOCUMENT_SCHEMAS,
        build_extraction_prompt,
        format_extracted_text,
    )

    assert "Commercial Invoice" in DOCUMENT_SCHEMAS
    assert "Packing List" in DOCUMENT_SCHEMAS
    assert "Purchase Order" in DOCUMENT_SCHEMAS
    assert "Shipping Bill" in DOCUMENT_SCHEMAS
    assert "Certificate of Origin" in DOCUMENT_SCHEMAS

    mock_pages = {1: "INVOICE #INV-2024-001\nTOTAL: 22500 EUR"}
    fmt = format_extracted_text(mock_pages)
    assert "--- PAGE 1 ---" in fmt

    prm = build_extraction_prompt("Commercial Invoice", fmt, DOCUMENT_SCHEMAS["Commercial Invoice"])
    assert "Commercial Invoice" in prm
    print("  PASS: server.document_intelligence schemas and prompt builders verified.")

    # 3. Test server.compliance (Validation Engine)
    print("\n[CHECK 3] Testing server.compliance (Cross-Document Engine)...")
    from server.compliance import (
        CrossDocumentValidator,
        validate_documents,
        clean_string,
        company_names_match,
        normalize_currency,
        normalize_hs_code,
        normalize_weight_to_kg,
    )
    from server.schemas.validation import ValidationStatus

    # Test normalizers
    assert company_names_match("Global Exports Ltd", "Global Exports Limited") is True
    assert normalize_currency("US$") == "USD"
    assert normalize_hs_code("8483.40.00") == "848340"
    assert normalize_weight_to_kg(1000, "g") == 1.0

    # Import mock documents from test_validation
    from test_validation import get_mock_documents

    docs = get_mock_documents()
    res1 = validate_documents(docs)
    assert res1.overall_compliance_status == ValidationStatus.PASS
    assert res1.summary.failed == 0
    print(f"  PASS: server.compliance engine evaluated 5 mock documents: {res1.summary.passed} checks passed.")

    # Test discrepancy injection
    mismatch_docs = get_mock_documents()
    mismatch_docs["Packing List"]["invoice_reference_number"] = "INV-WRONG-999"
    res2 = validate_documents(mismatch_docs)
    assert res2.overall_compliance_status == ValidationStatus.FAIL
    assert res2.summary.failed >= 1
    print(f"  PASS: server.compliance engine correctly flagged discrepancy ({res2.summary.failed} failed checks).")

    # 4. Test server.rules (Statutory Seeder and Checker)
    print("\n[CHECK 4] Testing server.rules (Statutory Seeder & Checker)...")
    from server.rules import (
        load_seed_rules,
        seed_regulatory_rules,
        extract_shipment_context,
        verify_government_rules,
    )
    from server.schemas.compliance import RegulatoryComplianceStatus

    seed_rules = load_seed_rules()
    assert len(seed_rules) == 8, f"Expected 8 statutory rules, found {len(seed_rules)}"
    print(f"  PASS: Loaded {len(seed_rules)} statutory rules from data/rules/.")

    count = seed_regulatory_rules()
    assert count == 8, f"Expected 8 indexed rules, got {count}"
    print(f"  PASS: Successfully seeded {count} statutory rules.")

    gov_report = verify_government_rules(docs)
    assert gov_report.overall_government_compliance in (
        RegulatoryComplianceStatus.COMPLIANT,
        RegulatoryComplianceStatus.NON_COMPLIANT,
        RegulatoryComplianceStatus.ADVISORY,
    )
    assert gov_report.summary.total_rules_evaluated > 0
    print(f"  PASS: server.rules statutory verification executed: evaluated {gov_report.summary.total_rules_evaluated} provisions.")

    print("\n================================================================================")
    print("  ALL STEP 3 BUSINESS LOGIC CHECKS PASSED WITH ZERO ERRORS!")
    print("================================================================================")


if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
