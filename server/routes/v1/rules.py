"""
Government Regulatory Rules Monitoring, Sync & Approval API Endpoints (v1).
Exposes overview metrics, active/withdrawn rule listings, live official notifications,
immutable version history, manual sync triggers, and manual_review rule approvals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from server.auth.dependencies import require_org_context
from server.auth.models import OrganizationContext
from server.repositories.rules_repository import RuleRegistryRepository
from server.rules.scheduler import get_rule_scheduler
from server.rules.sync_service import GovernmentRuleSyncService
from server.schemas.rules_monitoring import (
    GovernmentNotificationRecord,
    GovernmentRuleRecord,
    RuleSyncRunReport,
    RuleVersionHistoryEntry,
    RulesMonitoringOverview,
)

router = APIRouter(prefix="/rules", tags=["Government Rules Monitoring"])


@router.get(
    "/status",
    response_model=RulesMonitoringOverview,
    summary="Get Government Rules Monitoring Overview",
)
def get_rules_monitoring_status(
    ctx: OrganizationContext = Depends(require_org_context()),
) -> RulesMonitoringOverview:
    scheduler = get_rule_scheduler()
    service = GovernmentRuleSyncService()
    return service.get_overview(next_scheduled_sync=scheduler.next_run_iso)


@router.get(
    "",
    response_model=list[GovernmentRuleRecord],
    summary="List Stored Government Regulatory Rules",
)
def list_government_rules(
    source: str | None = Query(default=None, description="Filter by source (DGFT, CBIC, ICEGATE, RBI)"),
    lifecycle_status: str | None = Query(default=None, description="Filter by active, withdrawn, manual_review"),
    ctx: OrganizationContext = Depends(require_org_context()),
) -> list[GovernmentRuleRecord]:
    repo = RuleRegistryRepository()
    return repo.list_rules(source=source, lifecycle_status=lifecycle_status)


@router.get(
    "/notifications",
    response_model=list[GovernmentNotificationRecord],
    summary="List Latest Official Notifications Fetched",
)
def list_government_notifications(
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: OrganizationContext = Depends(require_org_context()),
) -> list[GovernmentNotificationRecord]:
    repo = RuleRegistryRepository()
    return repo.list_notifications(source=source, limit=limit)


@router.get(
    "/versions",
    response_model=list[RuleVersionHistoryEntry],
    summary="List Immutable Rule Version History",
)
def list_rule_version_history(
    rule_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    ctx: OrganizationContext = Depends(require_org_context()),
) -> list[RuleVersionHistoryEntry]:
    repo = RuleRegistryRepository()
    return repo.list_version_history(rule_id=rule_id, limit=limit)


@router.post(
    "/sync",
    response_model=RuleSyncRunReport,
    summary="Manually Sync Official Government Rules Now",
)
def sync_government_rules_now(
    ctx: OrganizationContext = Depends(require_org_context()),
) -> RuleSyncRunReport:
    service = GovernmentRuleSyncService()
    return service.sync_now(trigger="manual")


@router.post(
    "/{rule_id}/approve",
    response_model=GovernmentRuleRecord,
    summary="Approve a Manual-Review Rule for Active Compliance Verification",
)
def approve_manual_review_rule(
    rule_id: str,
    ctx: OrganizationContext = Depends(require_org_context()),
) -> GovernmentRuleRecord:
    service = GovernmentRuleSyncService()
    try:
        return service.approve_rule(rule_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{rule_id}/withdraw",
    response_model=GovernmentRuleRecord,
    summary="Withdraw a Superseded or Rescinded Rule and Remove from Vector Store",
)
def withdraw_government_rule(
    rule_id: str,
    reason: str = Query(default="Withdrawn per official government notice review."),
    ctx: OrganizationContext = Depends(require_org_context()),
) -> GovernmentRuleRecord:
    service = GovernmentRuleSyncService()
    try:
        return service.withdraw_rule(rule_id, reason=reason)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
