"""
Automatic Government Rule Diffing, Versioning, Approval & Vector Synchronization Service.
Compares live official notices from DGFT, ICEGATE, and CBIC against stored rules:
- Detects `new`, `modified`, `withdrawn`, `unchanged`, and `manual_review` changes.
- Records immutable `RuleVersionHistoryEntry` entries before applying changes.
- Upserts approved/validated active rules into Pinecone and deletes withdrawn rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from server.config.settings import get_settings
from server.integrations.embeddings import generate_embedding
from server.integrations.pinecone import delete_rules_from_pinecone, upsert_rules_to_pinecone
from server.logging.logger import get_logger
from server.repositories.rules_repository import RuleRegistryRepository, compute_rule_hash
from server.rules.fetcher import OFFICIAL_SOURCES, OfficialGovernmentRuleFetcher
from server.rules.validator import (
    deduplicate_notifications,
    notification_to_rule,
    validate_notification,
)
from server.schemas.rules_monitoring import (
    GovernmentNotificationRecord,
    GovernmentRuleRecord,
    GovernmentSourceInfo,
    RuleSyncRunReport,
    RuleVersionHistoryEntry,
    RulesMonitoringOverview,
    SourceSyncOutcome,
)

logger = get_logger("server.rules.sync_service")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rule_to_vector_record(rule: GovernmentRuleRecord) -> dict[str, Any]:
    embed_text = (
        f"AUTHORITY: {rule.authority}\n"
        f"POLICY: {rule.policy_document} ({rule.para_ref})\n"
        f"TITLE: {rule.rule_title}\n"
        f"SOURCE: {rule.source}\n"
        f"CONTENT: {rule.rule_text}"
    )
    vector = generate_embedding(embed_text, task_type="RETRIEVAL_DOCUMENT")
    return {
        "id": rule.rule_id,
        "values": vector,
        "metadata": {
            "rule_id": rule.rule_id,
            "source": rule.source,
            "authority": rule.authority,
            "notification_number": rule.notification_number,
            "category": rule.source,
            "policy_document": rule.policy_document,
            "section_or_para": rule.para_ref,
            "rule_title": rule.rule_title,
            "applicable_hs_prefixes": rule.applicable_hs_prefixes,
            "mandatory_documents": rule.mandatory_documents,
            "published_date": rule.published_date or "",
            "effective_date": rule.effective_date or "",
            "source_url": rule.source_url,
            "text": rule.rule_text,
            "is_active": rule.lifecycle_status == "active",
        },
    }


class GovernmentRuleSyncService:
    """Coordinates live fetch -> validate -> diff -> version -> store -> Pinecone sync."""

    def __init__(
        self,
        repository: RuleRegistryRepository | None = None,
        fetcher: OfficialGovernmentRuleFetcher | None = None,
    ) -> None:
        self.repo = repository or RuleRegistryRepository()
        self.fetcher = fetcher or OfficialGovernmentRuleFetcher()

    def sync_now(self, trigger: Literal["manual", "scheduled", "startup"] = "manual") -> RuleSyncRunReport:
        started_at = _utc_now_iso()
        sync_id = f"sync_{uuid.uuid4().hex[:12]}"

        existing_rules = {r.rule_id: r for r in self.repo.ensure_seeded()}
        raw_notifications, outcomes = self.fetcher.fetch_all_sources()

        deduped = deduplicate_notifications(raw_notifications)
        validated_notifications = [validate_notification(n) for n in deduped]
        self.repo.upsert_notifications(validated_notifications)

        outcome_map: dict[str, SourceSyncOutcome] = {o.source: o for o in outcomes}
        for n in validated_notifications:
            o = outcome_map.get(n.source)
            if o and n.validation_status == "validated":
                o.validated_count += 1

        new_count = 0
        updated_count = 0
        withdrawn_count = 0
        manual_review_count = 0

        to_upsert_vectors: list[dict[str, Any]] = []
        to_delete_rule_ids: list[str] = []

        for notif in validated_notifications:
            candidate = notification_to_rule(notif)
            existing = existing_rules.get(candidate.rule_id)
            outcome = outcome_map.get(notif.source)

            if existing is None:
                # Brand new rule discovered from official government source
                ver_entry = RuleVersionHistoryEntry(
                    version_id=f"ver_{candidate.rule_id}_v1_{uuid.uuid4().hex[:6]}",
                    rule_id=candidate.rule_id,
                    version_number=1,
                    change_type="manual_review" if candidate.lifecycle_status == "manual_review" else "new",
                    changed_at=_utc_now_iso(),
                    source=candidate.source,
                    notification_number=candidate.notification_number,
                    source_url=candidate.source_url,
                    effective_date=candidate.effective_date,
                    summary=(
                        f"Queued for manual review: {'; '.join(candidate.validation_notes)}"
                        if candidate.lifecycle_status == "manual_review"
                        else f"New {candidate.source} notice {candidate.notification_number} validated & activated."
                    ),
                    previous_state=None,
                    new_state=candidate.model_dump(),
                )
                self.repo.upsert_rule(candidate, version_entry=ver_entry)
                existing_rules[candidate.rule_id] = candidate

                if candidate.lifecycle_status == "active":
                    new_count += 1
                    if outcome:
                        outcome.new_count += 1
                    to_upsert_vectors.append(_rule_to_vector_record(candidate))
                else:
                    manual_review_count += 1
                    if outcome:
                        outcome.manual_review_count += 1
                continue

            # Existing rule matched — refresh verification timestamp if unchanged
            if existing.content_hash == candidate.content_hash and existing.lifecycle_status == candidate.lifecycle_status:
                refreshed = existing.model_copy(update={"last_verified_at": _utc_now_iso()})
                self.repo.upsert_rule(refreshed)
                existing_rules[refreshed.rule_id] = refreshed
                continue

            # Detect substantive modification — never overwrite silently without version history
            if notif.validation_status == "manual_review":
                # Keep previous active rule undisturbed in vector store until operator reviews, or record review note
                flagged = existing.model_copy(
                    update={
                        "lifecycle_status": "manual_review",
                        "verification_status": "manual_review",
                        "validation_notes": candidate.validation_notes,
                        "last_verified_at": _utc_now_iso(),
                    }
                )
                ver_entry = RuleVersionHistoryEntry(
                    version_id=f"ver_{existing.rule_id}_v{existing.version + 1}_{uuid.uuid4().hex[:6]}",
                    rule_id=existing.rule_id,
                    version_number=existing.version + 1,
                    change_type="manual_review",
                    changed_at=_utc_now_iso(),
                    source=candidate.source,
                    notification_number=candidate.notification_number,
                    source_url=candidate.source_url,
                    effective_date=candidate.effective_date,
                    summary=f"Modification detected requiring manual review: {'; '.join(candidate.validation_notes)}",
                    previous_state=existing.model_dump(),
                    new_state=candidate.model_dump(),
                )
                flagged = flagged.model_copy(update={"version": existing.version + 1})
                self.repo.upsert_rule(flagged, version_entry=ver_entry)
                existing_rules[flagged.rule_id] = flagged
                manual_review_count += 1
                if outcome:
                    outcome.manual_review_count += 1
                continue

            # Validated modification of an active rule
            new_version_num = existing.version + 1
            updated_rule = candidate.model_copy(
                update={
                    "version": new_version_num,
                    "last_verified_at": _utc_now_iso(),
                    "last_updated_at": _utc_now_iso(),
                }
            )
            ver_entry = RuleVersionHistoryEntry(
                version_id=f"ver_{existing.rule_id}_v{new_version_num}_{uuid.uuid4().hex[:6]}",
                rule_id=existing.rule_id,
                version_number=new_version_num,
                change_type="modified",
                changed_at=_utc_now_iso(),
                source=updated_rule.source,
                notification_number=updated_rule.notification_number,
                source_url=updated_rule.source_url,
                effective_date=updated_rule.effective_date,
                summary=f"Updated {updated_rule.source} rule from official notice {updated_rule.notification_number}.",
                previous_state=existing.model_dump(),
                new_state=updated_rule.model_dump(),
            )
            self.repo.upsert_rule(updated_rule, version_entry=ver_entry)
            existing_rules[updated_rule.rule_id] = updated_rule
            updated_count += 1
            if outcome:
                outcome.updated_count += 1
            to_upsert_vectors.append(_rule_to_vector_record(updated_rule))

        pinecone_upserted = upsert_rules_to_pinecone(to_upsert_vectors) if to_upsert_vectors else 0
        pinecone_deleted = delete_rules_from_pinecone(to_delete_rule_ids) if to_delete_rule_ids else 0

        success_sources = [o for o in outcomes if o.status == "success"]
        failed_sources = [o for o in outcomes if o.status != "success"]
        if len(success_sources) == len(outcomes):
            overall_status = "success"
            msg = f"Synced {len(validated_notifications)} unique official notices across all sources."
        elif success_sources:
            overall_status = "partial"
            failed_names = ", ".join(f"{o.source} ({o.status})" for o in failed_sources)
            msg = (
                f"Synced {len(validated_notifications)} notices from {', '.join(o.source for o in success_sources)}. "
                f"Unavailable sources: {failed_names}."
            )
        else:
            overall_status = "failed"
            msg = "All government sources were unreachable or failed verification; preserved existing rule set."

        all_rules_after = self.repo.list_rules()
        active_rules_after = [r for r in all_rules_after if r.lifecycle_status == "active"]
        withdrawn_total = sum(1 for r in all_rules_after if r.lifecycle_status == "withdrawn")

        report = RuleSyncRunReport(
            sync_id=sync_id,
            started_at=started_at,
            completed_at=_utc_now_iso(),
            trigger=trigger,
            overall_status=overall_status,  # type: ignore[arg-type]
            total_rules=len(all_rules_after),
            active_rules=len(active_rules_after),
            new_rules_detected=new_count,
            updated_rules=updated_count,
            withdrawn_rules=withdrawn_count or withdrawn_total,
            manual_review_rules=manual_review_count,
            notifications_fetched=len(validated_notifications),
            source_outcomes=outcomes,
            pinecone_upserted=pinecone_upserted,
            pinecone_deleted=pinecone_deleted,
            message=msg,
        )
        self.repo.record_sync_run(report)
        return report

    def approve_rule(self, rule_id: str) -> GovernmentRuleRecord:
        """Explicit operator approval promoting a `manual_review` rule to `active` and indexing in Pinecone."""
        existing = self.repo.get_rule(rule_id)
        if not existing:
            raise KeyError(f"Rule '{rule_id}' not found.")

        now = _utc_now_iso()
        new_version = existing.version + 1
        approved_dict = existing.model_dump()
        approved_dict.update(
            {
                "lifecycle_status": "active",
                "verification_status": "verified",
                "last_verified_at": now,
                "last_updated_at": now,
                "version": new_version,
                "validation_notes": list(existing.validation_notes) + ["Approved for active compliance checks."],
            }
        )
        approved_dict["content_hash"] = compute_rule_hash(approved_dict)
        approved = GovernmentRuleRecord(**approved_dict)

        ver_entry = RuleVersionHistoryEntry(
            version_id=f"ver_{rule_id}_v{new_version}_{uuid.uuid4().hex[:6]}",
            rule_id=rule_id,
            version_number=new_version,
            change_type="approved",
            changed_at=now,
            source=approved.source,
            notification_number=approved.notification_number,
            source_url=approved.source_url,
            effective_date=approved.effective_date,
            summary=f"Rule {rule_id} manually approved and indexed into Pinecone.",
            previous_state=existing.model_dump(),
            new_state=approved.model_dump(),
        )
        self.repo.upsert_rule(approved, version_entry=ver_entry)
        upsert_rules_to_pinecone([_rule_to_vector_record(approved)])
        return approved

    def withdraw_rule(self, rule_id: str, reason: str = "Withdrawn per official notice review.") -> GovernmentRuleRecord:
        """Marks a rule `withdrawn`, appends immutable history, and removes vector from Pinecone."""
        existing = self.repo.get_rule(rule_id)
        if not existing:
            raise KeyError(f"Rule '{rule_id}' not found.")

        now = _utc_now_iso()
        new_version = existing.version + 1
        withdrawn_dict = existing.model_dump()
        withdrawn_dict.update(
            {
                "lifecycle_status": "withdrawn",
                "verification_status": "withdrawn",
                "last_verified_at": now,
                "last_updated_at": now,
                "version": new_version,
                "validation_notes": list(existing.validation_notes) + [reason],
            }
        )
        withdrawn_dict["content_hash"] = compute_rule_hash(withdrawn_dict)
        withdrawn = GovernmentRuleRecord(**withdrawn_dict)

        ver_entry = RuleVersionHistoryEntry(
            version_id=f"ver_{rule_id}_v{new_version}_{uuid.uuid4().hex[:6]}",
            rule_id=rule_id,
            version_number=new_version,
            change_type="withdrawn",
            changed_at=now,
            source=withdrawn.source,
            notification_number=withdrawn.notification_number,
            source_url=withdrawn.source_url,
            effective_date=withdrawn.effective_date,
            summary=reason,
            previous_state=existing.model_dump(),
            new_state=withdrawn.model_dump(),
        )
        self.repo.upsert_rule(withdrawn, version_entry=ver_entry)
        delete_rules_from_pinecone([rule_id])
        return withdrawn

    def get_overview(self, next_scheduled_sync: str | None = None) -> RulesMonitoringOverview:
        settings = get_settings()
        rules = self.repo.list_rules()
        runs = self.repo.list_sync_runs(limit=10)
        versions = self.repo.list_version_history(limit=200)

        last_run = runs[0] if runs else None
        last_successful = next((r for r in runs if r.overall_status in ("success", "partial")), None)
        last_outcomes = {o.source: o for o in (last_run.source_outcomes if last_run else [])}

        sources_info: list[GovernmentSourceInfo] = []
        for src_key in ("DGFT", "CBIC", "ICEGATE"):
            meta = OFFICIAL_SOURCES[src_key]
            o = last_outcomes.get(src_key)
            sources_info.append(
                GovernmentSourceInfo(
                    source=src_key,  # type: ignore[arg-type]
                    label=meta["label"],
                    portal_url=meta["portal_url"],
                    last_status=o.status if o else "not_checked",
                    last_checked_at=o.checked_at if o else None,
                    last_error=o.error_message if o else None,
                )
            )

        return RulesMonitoringOverview(
            last_successful_sync=last_successful.completed_at if last_successful else None,
            last_sync_attempt=last_run.completed_at if last_run else None,
            last_sync_status=last_run.overall_status if last_run else "never_synced",
            last_sync_trigger=last_run.trigger if last_run else None,
            scheduler_enabled=settings.RULE_SYNC_ENABLED,
            scheduler_interval_hours=settings.RULE_SYNC_INTERVAL_HOURS,
            next_scheduled_sync=next_scheduled_sync,
            storage_backend=self.repo.get_storage_backend_name(),  # type: ignore[arg-type]
            government_sources=sources_info,
            total_rules=len(rules),
            active_rules=sum(1 for r in rules if r.lifecycle_status == "active"),
            new_rules_detected=last_run.new_rules_detected if last_run else sum(1 for r in rules if not r.is_seed_rule),
            updated_rules=last_run.updated_rules if last_run else sum(1 for v in versions if v.change_type == "modified"),
            withdrawn_rules=sum(1 for r in rules if r.lifecycle_status == "withdrawn"),
            manual_review_rules=sum(1 for r in rules if r.lifecycle_status == "manual_review"),
            recent_sync_runs=runs,
        )
