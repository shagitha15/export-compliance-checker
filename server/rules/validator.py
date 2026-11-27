"""
Government Rule Validator, Deduplicator & Rule Converter.
Validates parsed official notices before storing, deduplicates duplicates by
notification key and content hash, and routes uncertain or incomplete items to `manual_review`.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from server.repositories.rules_repository import compute_rule_hash
from server.schemas.rules_monitoring import (
    GovernmentNotificationRecord,
    GovernmentRuleRecord,
)

ALLOWED_OFFICIAL_DOMAINS = (
    "dgft.gov.in",
    "content.dgft.gov.in",
    "cbic.gov.in",
    "taxinformation.cbic.gov.in",
    "icegate.gov.in",
    "jawaharcustoms.gov.in",
    "rbi.org.in",
)

_WITHDRAWAL_PATTERN = re.compile(
    r"\b(?:withdrawn|rescinded|superseded|cancelled|stands\s+omitted|abolished)\b",
    re.I,
)


def is_official_source_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    host = parsed.netloc.lower().split(":")[0]
    return any(host == d or host.endswith(f".{d}") for d in ALLOWED_OFFICIAL_DOMAINS)


def deduplicate_notifications(
    notifications: list[GovernmentNotificationRecord],
) -> list[GovernmentNotificationRecord]:
    """Removes duplicate notifications within a single sync batch using ID and content hash."""
    seen_keys: set[tuple[str, str, str]] = set()
    seen_hashes: set[str] = set()
    unique: list[GovernmentNotificationRecord] = []

    for item in notifications:
        norm_key = (
            item.source.upper(),
            item.notification_number.strip().lower(),
            item.source_url.strip().lower(),
        )
        if norm_key in seen_keys or item.content_hash in seen_hashes:
            continue
        seen_keys.add(norm_key)
        seen_hashes.add(item.content_hash)
        unique.append(item)

    return unique


def validate_notification(item: GovernmentNotificationRecord) -> GovernmentNotificationRecord:
    """
    Validates required official metadata on a notification.
    Marks items with missing publication dates, non-official URLs, or uncertain withdrawal language
    as `manual_review` so unverified changes are never silently applied.
    """
    notes: list[str] = list(item.validation_notes)

    if not item.title or len(item.title.strip()) < 10:
        notes.append("Title missing or too short to verify regulatory requirement.")

    if not is_official_source_url(item.source_url):
        notes.append(f"Source URL '{item.source_url}' is not on an approved Indian government domain.")

    if not item.published_date:
        notes.append("Publication date missing or could not be parsed cleanly from official notice.")

    if _WITHDRAWAL_PATTERN.search(f"{item.title} {item.summary}"):
        notes.append("Notice mentions withdrawal/rescission/supersession; requires manual confirmation before deactivating active rules.")

    if not item.is_export_relevant:
        notes.append("Notice appears import-policy or general-administration focused; held for export compliance applicability review.")

    validation_status = "manual_review" if notes else "validated"
    return item.model_copy(
        update={
            "validation_status": validation_status,
            "validation_notes": notes,
        }
    )


def _infer_mandatory_documents(text: str) -> list[str]:
    lower = text.lower()
    docs: list[str] = []
    if "shipping bill" in lower:
        docs.append("Shipping Bill")
    if "commercial invoice" in lower or "invoice" in lower:
        docs.append("Commercial Invoice")
    if "packing list" in lower:
        docs.append("Packing List")
    if "bill of lading" in lower or "airway bill" in lower or "scmtr" in lower:
        docs.append("Bill of Lading")
    if "certificate of origin" in lower:
        docs.append("Certificate of Origin")
    if "lut" in lower or "letter of undertaking" in lower:
        docs.append("LUT")
    if "scomet" in lower or "authorisation" in lower or "license" in lower:
        docs.append("Export License / SCOMET")
    return docs


def _infer_severity(item: GovernmentNotificationRecord) -> str:
    combined = f"{item.title} {item.summary}".lower()
    if any(k in combined for k in ("prohibited", "scomet", "restricted", "mandatory", "ban", "closure", "suspension")):
        return "HIGH"
    if any(k in combined for k in ("amendment", "circular", "advisory", "scmtr", "filing")):
        return "MEDIUM"
    return "LOW"


def build_rule_id(item: GovernmentNotificationRecord) -> str:
    clean_num = re.sub(r"[^A-Za-z0-9]+", "_", item.notification_number.upper()).strip("_")
    if not clean_num or clean_num in ("UNNUMBERED", "CBIC_NOTICE"):
        clean_num = item.notification_id.upper()
    return f"{item.source.upper()}_{clean_num}"[:64]


def notification_to_rule(item: GovernmentNotificationRecord) -> GovernmentRuleRecord:
    """Converts a validated or review-flagged official notification into a GovernmentRuleRecord."""
    rule_id = build_rule_id(item)
    authority = {
        "DGFT": "DGFT",
        "CBIC": "CBIC Customs & GST",
        "ICEGATE": "ICEGATE / CBIC",
        "RBI": "RBI",
    }.get(item.source, item.source)

    is_validated = item.validation_status == "validated"
    lifecycle = "active" if is_validated else "manual_review"
    verification = "verified" if is_validated else "manual_review"
    combined_text = f"{item.title}. {item.summary}".strip()

    rule_dict = {
        "rule_id": rule_id,
        "source": item.source,
        "authority": authority,
        "notification_number": item.notification_number,
        "policy_document": f"{authority} {item.category} ({item.notification_number})",
        "para_ref": item.notification_number,
        "rule_title": item.title,
        "rule_text": combined_text,
        "applicable_hs_prefixes": item.hs_prefixes or ["ALL"],
        "mandatory_documents": _infer_mandatory_documents(combined_text),
        "severity": _infer_severity(item),
        "published_date": item.published_date,
        "effective_date": item.effective_date,
        "last_verified_at": item.last_verified_at,
        "last_updated_at": item.last_verified_at,
        "source_url": item.source_url,
        "lifecycle_status": lifecycle,
        "verification_status": verification,
        "validation_notes": item.validation_notes,
        "version": 1,
        "is_seed_rule": False,
    }
    rule_dict["content_hash"] = compute_rule_hash(rule_dict)
    return GovernmentRuleRecord(**rule_dict)
