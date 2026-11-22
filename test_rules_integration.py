"""
Unit test suite for Pinecone Government Rules Integration.
"""

import json
from services.rules import (
    GovernmentComplianceReport,
    RegulatoryComplianceStatus,
    query_regulatory_rules,
    seed_regulatory_rules,
    verify_government_rules,
)
from services.rules.embedding_service import generate_embedding
from test_validation import get_mock_documents


def run_tests():
    print("1. Testing Rule Seeding...")
    count = seed_regulatory_rules()
    print(f"✓ Seeded {count} statutory rules.")
    assert count >= 7, f"Expected at least 7 rules, found {count}"

    print("\n2. Testing Semantic Vector Search...")
    query_text = "Mandatory Importer Exporter Code and truthfulness declaration"
    query_vec = generate_embedding(query_text, task_type="RETRIEVAL_QUERY")
    results = query_regulatory_rules(query_vec, top_k=3)
    print(f"✓ Retrieved {len(results)} rules matching query.")
    for idx, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        print(f"   [{idx}] {r['rule_id']} (Score: {r['score']}): {meta.get('rule_title')}")
        print(f"       Source: {meta.get('source_url')}")
        assert meta.get("source_url"), "Source URL must be present"

    print("\n3. Testing Statutory Compliance Verification...")
    mock_docs = get_mock_documents()
    report: GovernmentComplianceReport = verify_government_rules(mock_docs)
    print(f"✓ Government Compliance Audit ID: {report.audit_id}")
    print(f"✓ Overall Statutory Status: {report.overall_government_compliance}")
    print(f"✓ Summary: {report.summary.model_dump()}")
    print("\nDetailed Findings:")
    for f in report.findings:
        print(f" • [{f.status}] {f.rule_id} ({f.authority} {f.para_ref}): {f.rule_title}")
        print(f"   Evidence: {f.observed_evidence}")
        print(f"   Source URL: {f.source_url}")

    assert report.summary.total_rules_evaluated > 0
    assert report.summary.compliant_count > 0
    print("\n All Pinecone Government Rules Integration tests passed successfully!")


if __name__ == "__main__":
    run_tests()
