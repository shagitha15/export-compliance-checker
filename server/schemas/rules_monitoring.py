"""
Pydantic Schemas for Real-Time Government Rule Fetching, Versioning & Monitoring.
Covers official source outcomes, fetched notifications, validated rule registry entries,
immutable rule version history, and sync summary reports.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


RuleSourceType = Literal["DGFT", "CBIC", "ICEGATE", "RBI", "CUSTOMS_SEED"]
RuleLifecycleStatus = Literal["active", "withdrawn", "manual_review", "superseded"]
VerificationStatus = Literal["verified", "manual_review", "seed_baseline", "withdrawn"]
ChangeType = Literal["new", "modified", "withdrawn", "unchanged", "manual_review", "approved"]
SourceOutcomeStatus = Literal["success", "tls_error", "network_error", "parse_error", "skipped"]
OverallSyncStatus = Literal["success", "partial", "failed", "never_synced"]


class GovernmentNotificationRecord(BaseModel):
    """Structured regulatory notification/circular/advisory extracted from official portals."""

    notification_id: str = Field(..., description="Deterministic dedup key across source + number + url")
    source: RuleSourceType
    category: str = Field(..., description="e.g. Notification, Public Notice, Circular, Advisory")
    notification_number: str = Field(default="Unnumbered")
    title: str
    summary: str = Field(default="")
    published_date: str | None = Field(default=None, description="ISO YYYY-MM-DD when explicitly available")
    effective_date: str | None = Field(default=None, description="ISO YYYY-MM-DD when explicitly stated")
    source_url: str
    attachment_url: str | None = None
    fetched_at: str
    last_verified_at: str
    content_hash: str
    validation_status: Literal["validated", "manual_review"] = "validated"
    validation_notes: list[str] = Field(default_factory=list)
    is_export_relevant: bool = True
    hs_prefixes: list[str] = Field(default_factory=lambda: ["ALL"])


class GovernmentRuleRecord(BaseModel):
    """Canonical structured export compliance rule backed by static seed or live official notice."""

    rule_id: str
    source: RuleSourceType = "DGFT"
    authority: str
    notification_number: str = Field(default="Statutory Baseline")
    policy_document: str
    para_ref: str = Field(default="Official Notice")
    rule_title: str
    rule_text: str
    applicable_hs_prefixes: list[str] = Field(default_factory=lambda: ["ALL"])
    mandatory_documents: list[str] = Field(default_factory=list)
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = "MEDIUM"
    published_date: str | None = None
    effective_date: str | None = None
    last_verified_at: str | None = None
    last_updated_at: str | None = None
    source_url: str
    lifecycle_status: RuleLifecycleStatus = "active"
    verification_status: VerificationStatus = "seed_baseline"
    validation_notes: list[str] = Field(default_factory=list)
    version: int = 1
    content_hash: str
    is_seed_rule: bool = False


class RuleVersionHistoryEntry(BaseModel):
    """Immutable audit log entry capturing rule creations, updates, withdrawals, or approvals."""

    version_id: str
    rule_id: str
    version_number: int
    change_type: ChangeType
    changed_at: str
    source: RuleSourceType
    notification_number: str
    source_url: str
    effective_date: str | None = None
    summary: str
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None


class SourceSyncOutcome(BaseModel):
    """Per-source network & parser telemetry from a sync execution."""

    source: Literal["DGFT", "CBIC", "ICEGATE"]
    source_url: str
    status: SourceOutcomeStatus
    fetched_count: int = 0
    validated_count: int = 0
    new_count: int = 0
    updated_count: int = 0
    withdrawn_count: int = 0
    manual_review_count: int = 0
    error_message: str | None = None
    checked_at: str


class RuleSyncRunReport(BaseModel):
    """Result returned by manual or scheduled sync execution."""

    sync_id: str
    started_at: str
    completed_at: str
    trigger: Literal["manual", "scheduled", "startup"]
    overall_status: OverallSyncStatus
    total_rules: int = 0
    active_rules: int = 0
    new_rules_detected: int = 0
    updated_rules: int = 0
    withdrawn_rules: int = 0
    manual_review_rules: int = 0
    notifications_fetched: int = 0
    source_outcomes: list[SourceSyncOutcome] = Field(default_factory=list)
    pinecone_upserted: int = 0
    pinecone_deleted: int = 0
    message: str = ""


class GovernmentSourceInfo(BaseModel):
    """Metadata describing configured official government source endpoints."""

    source: Literal["DGFT", "CBIC", "ICEGATE"]
    label: str
    portal_url: str
    last_status: SourceOutcomeStatus | Literal["not_checked"] = "not_checked"
    last_checked_at: str | None = None
    last_error: str | None = None


class RulesMonitoringOverview(BaseModel):
    """Top-level monitoring summary consumed by the frontend dashboard."""

    last_successful_sync: str | None = None
    last_sync_attempt: str | None = None
    last_sync_status: OverallSyncStatus = "never_synced"
    last_sync_trigger: str | None = None
    scheduler_enabled: bool = True
    scheduler_interval_hours: float = 24.0
    next_scheduled_sync: str | None = None
    storage_backend: Literal["supabase", "local_registry"] = "local_registry"
    government_sources: list[GovernmentSourceInfo] = Field(default_factory=list)
    total_rules: int = 0
    active_rules: int = 0
    new_rules_detected: int = 0
    updated_rules: int = 0
    withdrawn_rules: int = 0
    manual_review_rules: int = 0
    recent_sync_runs: list[RuleSyncRunReport] = Field(default_factory=list)
