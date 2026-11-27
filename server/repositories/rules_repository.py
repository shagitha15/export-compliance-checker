"""
Repository for Government Regulatory Rules, Notifications, Version History, and Sync Logs.
Uses Supabase PostgreSQL tables when applied via migration, with seamless atomic local JSON
fallback so rule updates and version tracking work reliably in single-user and local modes.
Always preserves `data/rules/indian_export_regulations.json` untouched as canonical seed/fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger
from server.schemas.rules_monitoring import (
    GovernmentNotificationRecord,
    GovernmentRuleRecord,
    RuleSyncRunReport,
    RuleVersionHistoryEntry,
)

logger = get_logger("server.repositories.rules")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_SEED_FILE = PROJECT_ROOT / "data" / "rules" / "indian_export_regulations.json"
LOCAL_REGISTRY_FILE = PROJECT_ROOT / "data" / "rules" / "regulatory_rules_registry.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_rule_hash(payload: dict[str, Any]) -> str:
    """Computes a stable SHA-256 hash over semantic regulatory rule fields."""
    canonical = {
        "rule_id": str(payload.get("rule_id") or "").strip(),
        "source": str(payload.get("source") or "").strip(),
        "notification_number": str(payload.get("notification_number") or "").strip(),
        "rule_title": str(payload.get("rule_title") or "").strip(),
        "rule_text": str(payload.get("rule_text") or "").strip(),
        "applicable_hs_prefixes": sorted(str(x).strip() for x in (payload.get("applicable_hs_prefixes") or ["ALL"])),
        "mandatory_documents": sorted(str(x).strip() for x in (payload.get("mandatory_documents") or [])),
        "effective_date": payload.get("effective_date") or None,
        "source_url": str(payload.get("source_url") or "").strip(),
        "lifecycle_status": str(payload.get("lifecycle_status") or "active").strip(),
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _infer_source_from_authority(authority: str, rule_id: str) -> str:
    text = f"{authority} {rule_id}".upper()
    if "DGFT" in text or "ITCHS" in text:
        return "DGFT"
    if "ICEGATE" in text:
        return "ICEGATE"
    if "CBIC" in text or "CUSTOMS" in text or "GST" in text:
        return "CBIC"
    if "RBI" in text or "FEMA" in text:
        return "RBI"
    return "DGFT"


def load_static_seed_records() -> list[GovernmentRuleRecord]:
    """Loads baseline rules from static JSON without modifying the original file."""
    if not STATIC_SEED_FILE.exists():
        logger.warning("Static seed rule file missing: %s", STATIC_SEED_FILE)
        return []

    raw_items = json.loads(STATIC_SEED_FILE.read_text(encoding="utf-8"))
    now = _utc_now_iso()
    records: list[GovernmentRuleRecord] = []
    for item in raw_items:
        source = _infer_source_from_authority(item.get("authority", ""), item.get("rule_id", ""))
        base = {
            "rule_id": item["rule_id"],
            "source": source,
            "authority": item.get("authority", "DGFT"),
            "notification_number": item.get("section_or_para") or item.get("para_ref") or item["rule_id"],
            "policy_document": item.get("policy_document", "Static Statutory Baseline"),
            "para_ref": item.get("section_or_para") or item.get("para_ref") or "Statutory Baseline",
            "rule_title": item["rule_title"],
            "rule_text": item.get("text") or item.get("rule_text") or "",
            "applicable_hs_prefixes": item.get("applicable_hs_prefixes", ["ALL"]),
            "mandatory_documents": item.get("mandatory_documents", []),
            "severity": item.get("severity", "HIGH" if item.get("prohibited_or_restricted") or item.get("requires_license") else "MEDIUM"),
            "published_date": None,
            "effective_date": item.get("effective_date"),
            "last_verified_at": None,
            "last_updated_at": now,
            "source_url": item.get("source_url", "https://www.dgft.gov.in/CP/"),
            "lifecycle_status": "active",
            "verification_status": "seed_baseline",
            "validation_notes": ["Loaded from static seed file data/rules/indian_export_regulations.json"],
            "version": 1,
            "is_seed_rule": True,
        }
        base["content_hash"] = compute_rule_hash(base)
        records.append(GovernmentRuleRecord(**base))
    return records


class RuleRegistryRepository:
    """Thread-safe repository persisting rules, notifications, versions, and sync telemetry."""

    _lock = threading.RLock()

    def __init__(self, registry_file: Path | None = None, use_supabase: bool = True) -> None:
        self.registry_file = registry_file or LOCAL_REGISTRY_FILE
        self.use_supabase = use_supabase
        self._supabase_tables_ready: bool | None = None

    def _check_supabase_ready(self, refresh: bool = False) -> bool:
        if not self.use_supabase:
            return False
        if self._supabase_tables_ready is not None and not refresh:
            return self._supabase_tables_ready

        try:
            client = get_supabase_client()
            client.table("regulatory_rules").select("rule_id").limit(1).execute()
            client.table("regulatory_notifications").select("notification_id").limit(1).execute()
            client.table("regulatory_rule_versions").select("version_id").limit(1).execute()
            client.table("regulatory_rule_sync_logs").select("sync_id").limit(1).execute()
            self._supabase_tables_ready = True
        except Exception as exc:
            logger.debug("Supabase monitoring tables unavailable, using local registry fallback: %s", exc)
            self._supabase_tables_ready = False
        return bool(self._supabase_tables_ready)

    def get_storage_backend_name(self) -> str:
        return "supabase" if self._check_supabase_ready() else "local_registry"

    def _read_local_state(self) -> dict[str, Any]:
        with self._lock:
            if not self.registry_file.exists():
                seed_records = load_static_seed_records()
                initial = {
                    "rules": [r.model_dump() for r in seed_records],
                    "notifications": [],
                    "versions": [
                        RuleVersionHistoryEntry(
                            version_id=f"ver_{r.rule_id}_v1",
                            rule_id=r.rule_id,
                            version_number=1,
                            change_type="new",
                            changed_at=r.last_updated_at or _utc_now_iso(),
                            source=r.source,
                            notification_number=r.notification_number,
                            source_url=r.source_url,
                            effective_date=r.effective_date,
                            summary="Initial static baseline rule seeded.",
                            previous_state=None,
                            new_state=r.model_dump(),
                        ).model_dump()
                        for r in seed_records
                    ],
                    "sync_runs": [],
                }
                self._write_local_state(initial)
                return initial

            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                data.setdefault("rules", [])
                data.setdefault("notifications", [])
                data.setdefault("versions", [])
                data.setdefault("sync_runs", [])
                return data
            except Exception as exc:
                logger.error("Failed reading local rule registry (%s); recovering from seed: %s", self.registry_file, exc)
                seed_records = load_static_seed_records()
                return {
                    "rules": [r.model_dump() for r in seed_records],
                    "notifications": [],
                    "versions": [],
                    "sync_runs": [],
                }

    def _write_local_state(self, state: dict[str, Any]) -> None:
        with self._lock:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(state, indent=2, ensure_ascii=False)
            fd, tmp_path = tempfile.mkstemp(prefix="reg_rules_", suffix=".json", dir=str(self.registry_file.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(serialized)
                os.replace(tmp_path, self.registry_file)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def ensure_seeded(self) -> list[GovernmentRuleRecord]:
        """Ensures baseline rules from static JSON exist in the active registry."""
        if self._check_supabase_ready():
            client = get_supabase_client()
            res = client.table("regulatory_rules").select("*").execute()
            rows = res.data or []
            if not rows:
                seed_records = load_static_seed_records()
                for record in seed_records:
                    self.upsert_rule(record, version_entry=RuleVersionHistoryEntry(
                        version_id=f"ver_{record.rule_id}_v1_{uuid.uuid4().hex[:6]}",
                        rule_id=record.rule_id,
                        version_number=1,
                        change_type="new",
                        changed_at=record.last_updated_at or _utc_now_iso(),
                        source=record.source,
                        notification_number=record.notification_number,
                        source_url=record.source_url,
                        effective_date=record.effective_date,
                        summary="Initial static baseline rule seeded.",
                        previous_state=None,
                        new_state=record.model_dump(),
                    ))
                return seed_records
            return [GovernmentRuleRecord(**r) for r in rows]

        state = self._read_local_state()
        return [GovernmentRuleRecord(**r) for r in state.get("rules", [])]

    def list_rules(
        self,
        source: str | None = None,
        lifecycle_status: str | None = None,
        include_withdrawn: bool = True,
    ) -> list[GovernmentRuleRecord]:
        rules = self.ensure_seeded()
        filtered: list[GovernmentRuleRecord] = []
        for r in rules:
            if source and r.source.upper() != source.upper():
                continue
            if not include_withdrawn and r.lifecycle_status == "withdrawn":
                continue
            if lifecycle_status and r.lifecycle_status != lifecycle_status:
                continue
            filtered.append(r)
        filtered.sort(key=lambda item: (item.last_updated_at or "", item.published_date or "", item.rule_id), reverse=True)
        return filtered

    def list_active_verified_rules(self) -> list[GovernmentRuleRecord]:
        """Returns active rules eligible for vector search & live compliance verification."""
        rules = self.ensure_seeded()
        return [
            r
            for r in rules
            if r.lifecycle_status == "active" and r.verification_status in ("verified", "seed_baseline")
        ]

    def get_rule(self, rule_id: str) -> GovernmentRuleRecord | None:
        for r in self.ensure_seeded():
            if r.rule_id == rule_id:
                return r
        return None

    def upsert_rule(
        self,
        rule: GovernmentRuleRecord,
        version_entry: RuleVersionHistoryEntry | None = None,
    ) -> GovernmentRuleRecord:
        if self._check_supabase_ready():
            client = get_supabase_client()
            payload = rule.model_dump()
            payload["updated_at"] = _utc_now_iso()
            client.table("regulatory_rules").upsert(payload, on_conflict="rule_id").execute()
            if version_entry:
                client.table("regulatory_rule_versions").insert(version_entry.model_dump()).execute()
            return rule

        with self._lock:
            state = self._read_local_state()
            rules_list = state["rules"]
            replaced = False
            for idx, existing in enumerate(rules_list):
                if existing.get("rule_id") == rule.rule_id:
                    rules_list[idx] = rule.model_dump()
                    replaced = True
                    break
            if not replaced:
                rules_list.append(rule.model_dump())

            if version_entry:
                state["versions"].insert(0, version_entry.model_dump())
                state["versions"] = state["versions"][:500]
            self._write_local_state(state)
        return rule

    def upsert_notifications(self, notifications: list[GovernmentNotificationRecord]) -> list[GovernmentNotificationRecord]:
        if not notifications:
            return []

        if self._check_supabase_ready():
            client = get_supabase_client()
            for n in notifications:
                client.table("regulatory_notifications").upsert(
                    n.model_dump(), on_conflict="notification_id"
                ).execute()
            return notifications

        with self._lock:
            state = self._read_local_state()
            existing_map = {item["notification_id"]: idx for idx, item in enumerate(state["notifications"])}
            for n in notifications:
                dumped = n.model_dump()
                if n.notification_id in existing_map:
                    state["notifications"][existing_map[n.notification_id]] = dumped
                else:
                    state["notifications"].insert(0, dumped)
                    existing_map = {item["notification_id"]: idx for idx, item in enumerate(state["notifications"])}
            state["notifications"] = state["notifications"][:300]
            self._write_local_state(state)
        return notifications

    def list_notifications(self, source: str | None = None, limit: int = 50) -> list[GovernmentNotificationRecord]:
        if self._check_supabase_ready():
            client = get_supabase_client()
            q = client.table("regulatory_notifications").select("*")
            if source:
                q = q.eq("source", source.upper())
            res = q.order("fetched_at", desc=True).limit(limit).execute()
            return [GovernmentNotificationRecord(**row) for row in (res.data or [])]

        state = self._read_local_state()
        items = [GovernmentNotificationRecord(**row) for row in state.get("notifications", [])]
        if source:
            items = [i for i in items if i.source.upper() == source.upper()]
        items.sort(key=lambda i: (i.published_date or "", i.fetched_at), reverse=True)
        return items[:limit]

    def list_version_history(self, rule_id: str | None = None, limit: int = 100) -> list[RuleVersionHistoryEntry]:
        if self._check_supabase_ready():
            client = get_supabase_client()
            q = client.table("regulatory_rule_versions").select("*")
            if rule_id:
                q = q.eq("rule_id", rule_id)
            res = q.order("changed_at", desc=True).limit(limit).execute()
            return [RuleVersionHistoryEntry(**row) for row in (res.data or [])]

        state = self._read_local_state()
        entries = [RuleVersionHistoryEntry(**row) for row in state.get("versions", [])]
        if rule_id:
            entries = [e for e in entries if e.rule_id == rule_id]
        entries.sort(key=lambda e: e.changed_at, reverse=True)
        return entries[:limit]

    def record_sync_run(self, report: RuleSyncRunReport) -> RuleSyncRunReport:
        if self._check_supabase_ready():
            client = get_supabase_client()
            client.table("regulatory_rule_sync_logs").insert(report.model_dump()).execute()
            return report

        with self._lock:
            state = self._read_local_state()
            state["sync_runs"].insert(0, report.model_dump())
            state["sync_runs"] = state["sync_runs"][:50]
            self._write_local_state(state)
        return report

    def list_sync_runs(self, limit: int = 10) -> list[RuleSyncRunReport]:
        if self._check_supabase_ready():
            client = get_supabase_client()
            res = client.table("regulatory_rule_sync_logs").select("*").order("completed_at", desc=True).limit(limit).execute()
            return [RuleSyncRunReport(**row) for row in (res.data or [])]

        state = self._read_local_state()
        runs = [RuleSyncRunReport(**row) for row in state.get("sync_runs", [])]
        runs.sort(key=lambda r: r.completed_at, reverse=True)
        return runs[:limit]
