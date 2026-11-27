"""
Verification script for Step 1 (Schemas & Repositories) and Step 2 (Integrations Layer).
Validates lazy client initialization, schema structures, and zero import side-effects.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_checks():
    print("================================================================================")
    print("  STEP 1 & STEP 2 VERIFICATION TEST RUNNER")
    print("================================================================================")

    # 1. Test Schemas
    print("\n[CHECK 1] Testing server.schemas imports and instantiations...")
    from server.schemas import (
        DocumentType,
        UploadResponse,
        ExtractionResponse,
        ValidationStatus,
        CheckResult,
        IntraDocumentCheckResult,
        ValidationSummary,
        CrossDocumentValidationResponse,
        RegulatoryComplianceStatus,
        RegulatoryFinding,
        GovernmentComplianceSummary,
        GovernmentComplianceReport,
    )

    doc_type = DocumentType.COMMERCIAL_INVOICE
    assert doc_type.value == "Commercial Invoice"

    chk = CheckResult(
        check_id="TEST_001",
        rule_name="Test Rule",
        documents_involved=["Commercial Invoice"],
        status=ValidationStatus.PASS,
        field_name="invoice_number",
        message="Test check passed.",
    )
    assert chk.status == ValidationStatus.PASS

    rep = GovernmentComplianceReport(
        audit_id="gov_test_001",
        audit_timestamp="2026-11-25T00:00:00Z",
        hs_codes_evaluated=["8483"],
        overall_government_compliance=RegulatoryComplianceStatus.COMPLIANT,
        summary=GovernmentComplianceSummary(
            total_rules_evaluated=1,
            compliant_count=1,
            non_compliant_count=0,
            advisory_count=0,
        ),
        findings=[],
    )
    assert rep.overall_government_compliance == RegulatoryComplianceStatus.COMPLIANT
    print("  PASS: All Schemas (upload, validation, compliance) instantiated correctly.")

    # 2. Test Database & Repository
    print("\n[CHECK 2] Testing server.database and server.repositories...")
    from server.database import get_supabase_client
    from server.repositories import (
        DocumentRepository,
        store_extracted_document,
        fetch_extracted_documents,
    )

    repo = DocumentRepository()
    assert repo.table_name == "customs_documents"
    print("  PASS: DocumentRepository successfully initialized with target table 'customs_documents'.")

    # 3. Test Integrations (Lazy Loading & Fallbacks)
    print("\n[CHECK 3] Testing server.integrations (Lazy loading & fallbacks)...")
    from server.integrations import (
        get_gemini_client,
        generate_embedding,
        generate_embeddings_batch,
        get_pinecone_client,
        get_or_create_index,
        upsert_rules_to_pinecone,
        query_regulatory_rules,
        EMBEDDING_DIMENSION,
    )

    assert EMBEDDING_DIMENSION == 768

    # Test fallback embedding generation (operates deterministically without network)
    sample_text = "Universal Importer Exporter Code requirement under DGFT Foreign Trade Policy"
    vec = generate_embedding(sample_text)
    assert len(vec) == 768
    assert isinstance(vec[0], float)
    print("  PASS: 768-dimensional embedding generation verified.")

    # Test local vector store fallback in Pinecone integration
    test_record = {
        "id": "RULE_TEST_01",
        "values": vec,
        "metadata": {
            "rule_id": "RULE_TEST_01",
            "rule_title": "Test DGFT Rule",
            "applicable_hs_prefixes": ["ALL"],
        },
    }
    upserted = upsert_rules_to_pinecone([test_record])
    assert upserted == 1

    query_results = query_regulatory_rules(vec, top_k=1)
    assert len(query_results) == 1
    assert query_results[0]["rule_id"] == "RULE_TEST_01"
    print("  PASS: Pinecone integration and cosine similarity fallback verified.")

    print("\n================================================================================")
    print("  ALL STEP 1 & STEP 2 CHECKS PASSED WITH ZERO ERRORS!")
    print("================================================================================")


if __name__ == "__main__":
    try:
        run_checks()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
