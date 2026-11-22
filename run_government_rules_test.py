"""
Execution and Verification Script for Pinecone Government Rules Integration.
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


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_stored_rules_verification():
    print_separator("TEST 1: VERIFY ALL 8 STATUTORY RULES STORED IN PINECONE INDEX")
    count = seed_regulatory_rules()
    print(f"Total statutory rules seeded & indexed: {count} / 8")
    assert count == 8, f"Expected 8 rules, found {count}"

    from services.rules.rule_seeder import load_seed_rules
    rules = load_seed_rules()
    print("\nList of Indexed Statutory Rules:")
    for idx, r in enumerate(rules, 1):
        print(f" {idx}. [{r['rule_id']}] ({r['authority']}) {r['rule_title']}")
        print(f"    Policy: {r['policy_document']} - {r['section_or_para']}")
        print(f"    Source: {r['source_url']}")


def test_semantic_search():
    print_separator("TEST 2: SEMANTIC SEARCH WITH 4 STATUTORY QUERIES")
    test_queries = [
        ("IEC requirement", None),
        ("HS Code 8483 export policy", "8483"),
        ("Shipping Bill declaration under Customs Act Section 50", None),
        ("LUT / IGST export requirements", None),
    ]

    for q_idx, (query_text, hs_filter) in enumerate(test_queries, 1):
        print(f"\n--- Query {q_idx}: \"{query_text}\" (HS Filter: {hs_filter or 'None'}) ---")
        q_vec = generate_embedding(query_text, task_type="RETRIEVAL_QUERY")
        matches = query_regulatory_rules(q_vec, top_k=2, hs_prefix=hs_filter)
        
        for m_idx, m in enumerate(matches, 1):
            meta = m.get("metadata", {})
            print(f"  Result {m_idx}: [{m['rule_id']}] (Score: {m['score']})")
            print(f"    Authority: {meta.get('authority')}")
            print(f"    Title:     {meta.get('rule_title')}")
            print(f"    Para Ref:  {meta.get('policy_document')} ({meta.get('section_or_para')})")
            print(f"    Source:    {meta.get('source_url')}")
            print(f"    Text:      {meta.get('text')[:120]}...")


def test_compliant_shipment():
    print_separator("TEST 3A: RULE CHECKER - COMPLIANT SHIPMENT")
    docs = get_mock_documents()
    docs["Commercial Invoice"]["declaration_and_signatory"] = {
        "signatory_name": "Rajesh Kumar",
        "designation": "Director",
        "declaration_text": "We declare that this invoice shows the actual price of the goods and that all particulars are true and correct under Section 50 Customs Act.",
    }
    report: GovernmentComplianceReport = verify_government_rules(docs)

    print(f"Audit ID: {report.audit_id}")
    print(f"Overall Statutory Status: {report.overall_government_compliance.value}")
    print(f"Summary: {report.summary.model_dump()}")
    print("\nDetailed Findings:")
    for f in report.findings:
        print(f" • [{f.status.value}] {f.rule_id} | Authority: {f.authority} ({f.para_ref})")
        print(f"   Title:       {f.rule_title}")
        print(f"   Source URL:  {f.source_url}")
        print(f"   Evidence:    {f.observed_evidence}")

    assert report.overall_government_compliance == RegulatoryComplianceStatus.COMPLIANT
    assert report.summary.non_compliant_count == 0


def test_missing_iec_shipment():
    print_separator("TEST 3B: RULE CHECKER - SHIPMENT MISSING IEC DETAILS")
    docs = get_mock_documents()
    # Strip IEC and Tax ID from Commercial Invoice and Shipping Bill
    docs["Commercial Invoice"]["exporter_seller"]["tax_id_or_gstin"] = None
    docs["Commercial Invoice"]["exporter_seller"]["iec"] = None
    docs["Shipping Bill"]["iec"] = None
    docs["Shipping Bill"]["gstin"] = None

    report: GovernmentComplianceReport = verify_government_rules(docs)

    print(f"Audit ID: {report.audit_id}")
    print(f"Overall Statutory Status: {report.overall_government_compliance.value}")
    print(f"Summary: {report.summary.model_dump()}")
    print("\nDetailed Findings:")
    iec_finding = None
    for f in report.findings:
        if f.rule_id == "DGFT_FTP2023_P2_05":
            iec_finding = f
        print(f" • [{f.status.value}] {f.rule_id} | Authority: {f.authority} ({f.para_ref})")
        print(f"   Title:       {f.rule_title}")
        print(f"   Source URL:  {f.source_url}")
        print(f"   Evidence:    {f.observed_evidence}")
        if f.action_required:
            print(f"   Action Req:  {f.action_required}")

    assert report.overall_government_compliance == RegulatoryComplianceStatus.NON_COMPLIANT
    assert iec_finding is not None
    assert iec_finding.status == RegulatoryComplianceStatus.NON_COMPLIANT
    print("\n✓ Correctly identified missing IEC as NON_COMPLIANT with actionable guidance.")


def test_restricted_commodity_shipment():
    print_separator("TEST 3C: RULE CHECKER - RESTRICTED EXPORT PRODUCT WITHOUT AUTHORIZATION")
    docs = get_mock_documents()
    # Inject SCOMET restricted dual-use commodity without an export license
    docs["Commercial Invoice"]["line_items"] = [
        {
            "item_no": 1,
            "description": "SCOMET Dual-Use Inertial Navigation Laser Gyroscope System",
            "hs_code": "9014.20",
            "quantity": 5,
            "unit": "PCS",
            "unit_price": 12000.0,
            "total_amount": 60000.0,
        }
    ]
    docs["Shipping Bill"]["items"] = [
        {
            "item_no": 1,
            "description": "SCOMET Dual-Use Inertial Navigation Laser Gyroscope System",
            "ritc_hs_code": "90142000",
            "quantity": 5,
            "unit": "PCS",
            "fob_value": 60000.0,
        }
    ]
    docs["Shipping Bill"]["scheme_code"] = None

    report: GovernmentComplianceReport = verify_government_rules(docs)

    print(f"Audit ID: {report.audit_id}")
    print(f"Overall Statutory Status: {report.overall_government_compliance.value}")
    print(f"Summary: {report.summary.model_dump()}")
    print("\nDetailed Findings:")
    scomet_finding = None
    for f in report.findings:
        if f.rule_id == "DGFT_SCOMET_GEN":
            scomet_finding = f
        print(f" • [{f.status.value}] {f.rule_id} | Authority: {f.authority} ({f.para_ref})")
        print(f"   Title:       {f.rule_title}")
        print(f"   Source URL:  {f.source_url}")
        print(f"   Evidence:    {f.observed_evidence}")
        if f.action_required:
            print(f"   Action Req:  {f.action_required}")

    assert report.overall_government_compliance == RegulatoryComplianceStatus.NON_COMPLIANT
    assert scomet_finding is not None
    assert scomet_finding.status == RegulatoryComplianceStatus.NON_COMPLIANT
    print("\n✓ Correctly identified restricted dual-use SCOMET item as NON_COMPLIANT.")


if __name__ == "__main__":
    test_stored_rules_verification()
    test_semantic_search()
    test_compliant_shipment()
    test_missing_iec_shipment()
    test_restricted_commodity_shipment()
    print_separator("ALL 5 TESTS COMPLETED AND VERIFIED SUCCESSFULLY")
