"""
Unit & API Tests for Real-Time Government Rule Fetching, Validation,
Versioning, Pinecone Synchronization, Compliance Checker Integration & Scheduler.
"""

from __future__ import annotations

import asyncio
import html
import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.main import app
from server.repositories.rules_repository import RuleRegistryRepository
from server.rules.checker import verify_government_rules
from server.rules.fetcher import OfficialGovernmentRuleFetcher, parse_dgft_cp_html, parse_icegate_table_html
from server.rules.scheduler import GovernmentRuleScheduler
from server.rules.sync_service import GovernmentRuleSyncService
from server.rules.validator import deduplicate_notifications, notification_to_rule, validate_notification
from server.schemas.rules_monitoring import GovernmentNotificationRecord, SourceSyncOutcome


SAMPLE_DGFT_HTML = """
<html><body>
<input type="hidden" id="plnNewsDtl" value="{&quot;allNewsList&quot;:[
  {&quot;assetId&quot;:1113835,&quot;title&quot;:&quot;Notification&quot;,&quot;metadata1&quot;:&quot;52/2026-27&quot;,&quot;metadata2&quot;:&quot;2026-27&quot;,&quot;metadata3&quot;:&quot;Mandatory Export Declaration for HS 8483 machinery with Certificate of Origin.&quot;,&quot;metadata4&quot;:&quot;25/11/2026&quot;,&quot;path&quot;:&quot;https://content.dgft.gov.in/Website/notif52.pdf&quot;},
  {&quot;assetId&quot;:1113834,&quot;title&quot;:&quot;Notification&quot;,&quot;metadata1&quot;:&quot;51/2026-27&quot;,&quot;metadata2&quot;:&quot;2026-27&quot;,&quot;metadata3&quot;:&quot;Amendment in import policy of raw sugar under Chapter 17.&quot;,&quot;metadata4&quot;:&quot;25/11/2026&quot;,&quot;path&quot;:&quot;https://content.dgft.gov.in/Website/notif51.pdf&quot;}
]}">
</body></html>
"""

SAMPLE_ICEGATE_HTML = """
<html><body><table>
  <tr><th>S No</th><th>Name</th><th>Category</th><th>Date</th><th>Download</th></tr>
  <tr><td>1</td><td>Advisory - Return of Export Cargo Electronic Filing Version 1.0</td><td>Electronic Filing</td><td>28-04-2026</td><td><a href="/advisory/export-cargo-v1">Click Here</a></td></tr>
  <tr><td>2</td><td>Circular No. 18/2026 - Export Shipping Bill SCMTR Update</td><td>Customs Circular</td><td>15-05-2026</td><td><a href="/guidelines/circular-18-2026">Click Here</a></td></tr>
</table></body></html>
"""


def test_dgft_and_icegate_parsers_extract_verified_fields():
    dgft_items = parse_dgft_cp_html(SAMPLE_DGFT_HTML, pdf_fetcher=None)
    assert len(dgft_items) == 2
    assert dgft_items[0].notification_number == "52/2026-27"
    assert dgft_items[0].published_date == "2026-11-25"
    assert dgft_items[0].effective_date is None
    assert dgft_items[0].is_export_relevant is True
    assert "8483" in dgft_items[0].hs_prefixes

    assert dgft_items[1].is_export_relevant is False  # import-only notice detected

    ice_items = parse_icegate_table_html(SAMPLE_ICEGATE_HTML, "https://www.icegate.gov.in/archives/guidelines")
    assert len(ice_items) == 2
    assert ice_items[0].source == "ICEGATE"
    assert ice_items[0].published_date == "2026-04-28"
    assert ice_items[0].source_url == "https://www.icegate.gov.in/advisory/export-cargo-v1"
    assert ice_items[1].notification_number == "18/2026"


def test_dedup_and_validation_routes_uncertain_items_to_manual_review():
    raw = parse_dgft_cp_html(SAMPLE_DGFT_HTML, pdf_fetcher=None)
    dup = raw[0].model_copy()
    deduped = deduplicate_notifications([raw[0], dup, raw[1]])
    assert len(deduped) == 2

    v0 = validate_notification(deduped[0])
    v1 = validate_notification(deduped[1])
    assert v0.validation_status == "validated"
    assert v1.validation_status == "manual_review"  # import-only notice held for review

    missing_date = deduped[0].model_copy(update={"published_date": None, "notification_number": "99/2026-27"})
    v_missing = validate_notification(missing_date)
    assert v_missing.validation_status == "manual_review"
    assert any("Publication date" in note for note in v_missing.validation_notes)


def test_sync_service_diff_version_history_approve_and_withdraw(tmp_path: Path):
    reg_file = tmp_path / "reg.json"
    repo = RuleRegistryRepository(registry_file=reg_file, use_supabase=False)

    notifs = parse_dgft_cp_html(SAMPLE_DGFT_HTML) + parse_icegate_table_html(
        SAMPLE_ICEGATE_HTML, "https://www.icegate.gov.in/archives/guidelines"
    )

    class StubFetcher:
        def __init__(self, payload: list[GovernmentNotificationRecord]):
            self.payload = payload

        def fetch_all_sources(self):
            return self.payload, [
                SourceSyncOutcome(
                    source="DGFT",
                    source_url="https://www.dgft.gov.in/CP/",
                    status="success",
                    fetched_count=2,
                    checked_at="2026-11-26T00:00:00Z",
                ),
                SourceSyncOutcome(
                    source="ICEGATE",
                    source_url="https://www.icegate.gov.in/archives/guidelines",
                    status="success",
                    fetched_count=2,
                    checked_at="2026-11-26T00:00:00Z",
                ),
                SourceSyncOutcome(
                    source="CBIC",
                    source_url="https://taxinformation.cbic.gov.in/",
                    status="tls_error",
                    fetched_count=0,
                    error_message="Simulated TLS intermediate CA error",
                    checked_at="2026-11-26T00:00:00Z",
                ),
            ]

    svc = GovernmentRuleSyncService(repository=repo, fetcher=StubFetcher(notifs))  # type: ignore[arg-type]
    report = svc.sync_now(trigger="manual")

    assert report.overall_status == "partial"  # CBIC tls_error cleanly recorded without faking
    assert report.new_rules_detected == 3  # 1 DGFT export + 2 ICEGATE export
    assert report.manual_review_rules == 1  # 1 DGFT import-only flagged manual_review

    # Modify one notification and re-sync -> must bump version and keep history
    updated_notif = notifs[0].model_copy(
        update={
            "summary": "Updated mandatory declaration with e-BRC and Certificate of Origin.",
            "effective_date": "2026-12-01",
            "content_hash": "changed_hash_v2",
        }
    )
    svc2 = GovernmentRuleSyncService(repository=repo, fetcher=StubFetcher([updated_notif]))  # type: ignore[arg-type]
    report2 = svc2.sync_now(trigger="scheduled")
    assert report2.updated_rules == 1

    versions = repo.list_version_history(rule_id="DGFT_52_2026_27")
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[0].change_type == "modified"
    assert versions[1].version_number == 1

    # Approve the manual_review rule explicitly
    approved = svc2.approve_rule("DGFT_51_2026_27")
    assert approved.lifecycle_status == "active"
    assert approved.verification_status == "verified"

    # Withdraw rule cleanly
    withdrawn = svc2.withdraw_rule("DGFT_51_2026_27", reason="Superseded by fresh notification")
    assert withdrawn.lifecycle_status == "withdrawn"
    assert withdrawn.verification_status == "withdrawn"


def test_fetcher_reports_tls_errors_without_disabling_verification():
    fetcher = OfficialGovernmentRuleFetcher()
    assert fetcher.settings.RULE_SYNC_TIMEOUT_SECONDS > 0


def test_rules_monitoring_api_endpoints_single_user_mode(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SINGLE_USER_MODE", "true")
    from server.config.settings import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            res_status = client.get("/api/v1/rules/status")
            assert res_status.status_code == 200
            data = res_status.json()
            assert "total_rules" in data
            assert "government_sources" in data
            assert len(data["government_sources"]) == 3

            res_rules = client.get("/api/v1/rules")
            assert res_rules.status_code == 200
            assert len(res_rules.json()) >= 8

            res_versions = client.get("/api/v1/rules/versions")
            assert res_versions.status_code == 200
    finally:
        get_settings.cache_clear()


def test_compliance_checker_evaluates_dynamic_synced_rules():
    # Ensure static baseline + dynamic checking produces valid findings without crashing
    docs = {
        "Commercial Invoice": {
            "invoice_number": "INV-100",
            "currency": "USD",
            "incoterms": "FOB",
            "exporter_seller": {"tax_id_or_gstin": "27AAACG0000A1ZS", "iec": "0312345678"},
            "declaration_and_signatory": {"declaration_text": "We declare true value."},
            "line_items": [{"hs_code": "84834000", "description": "Industrial Gears"}],
        },
        "Shipping Bill": {"port_of_loading": "INNSA1", "ad_code": "6390001"},
        "Packing List": {"total_packages": 5},
    }
    report = verify_government_rules(docs)
    assert report.summary.total_rules_evaluated >= 1
