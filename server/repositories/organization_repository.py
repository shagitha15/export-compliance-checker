"""
Organization and Membership Repository for Multi-Tenant RBAC in Supabase PostgreSQL.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from server.auth.models import OrgRole
from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger

logger = get_logger("server.repositories.organization")


class SchemaMigrationRequiredError(RuntimeError):
    """Raised when Phase 2 Supabase schema tables have not been applied yet."""


def _is_missing_table_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "pgrst205" in msg or "could not find the table" in msg or "does not exist" in msg


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "org"
    return f"{base[:36]}-{uuid.uuid4().hex[:6]}"


class OrganizationRepository:
    """Manages organizations and organization_memberships with strict user scoping."""

    ORGS_TABLE = "organizations"
    MEMBERS_TABLE = "organization_memberships"

    def create_organization(
        self,
        name: str,
        creator_user_id: str,
        creator_email: str,
        iec: str | None = None,
        gstin: str | None = None,
    ) -> dict[str, Any]:
        if not name or not name.strip():
            raise ValueError("Organization name is required.")

        client = get_supabase_client()
        org_payload = {
            "name": name.strip(),
            "slug": _slugify(name),
            "iec": iec.strip().upper() if iec else None,
            "gstin": gstin.strip().upper() if gstin else None,
            "created_by": creator_user_id,
        }

        try:
            org_res = client.table(self.ORGS_TABLE).insert(org_payload).execute()
            if not org_res.data:
                raise RuntimeError("Organization creation returned empty response.")
            org = org_res.data[0]

            member_payload = {
                "organization_id": org["id"],
                "user_id": creator_user_id,
                "user_email": creator_email,
                "role": OrgRole.ADMIN.value,
                "status": "active",
                "invited_by": creator_user_id,
            }
            mem_res = client.table(self.MEMBERS_TABLE).insert(member_payload).execute()
            membership = mem_res.data[0] if mem_res.data else member_payload
            return {
                "organization": org,
                "membership": membership,
            }
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError(
                    "Phase 2 database tables ('organizations', 'organization_memberships') are not applied yet. "
                    "Execute supabase/migrations/20261125000001_phase2_enterprise_schema.sql in Supabase."
                ) from exc
            logger.error("Failed to create organization '%s': %s", name, exc)
            raise

    def list_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        client = get_supabase_client()
        try:
            mem_res = (
                client.table(self.MEMBERS_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "active")
                .order("created_at", desc=False)
                .execute()
            )
            memberships = mem_res.data or []
            if not memberships:
                return []

            org_ids = list({m["organization_id"] for m in memberships})
            orgs_res = client.table(self.ORGS_TABLE).select("*").in_("id", org_ids).execute()
            orgs_by_id = {str(o["id"]): o for o in (orgs_res.data or [])}

            results: list[dict[str, Any]] = []
            for m in memberships:
                oid = str(m["organization_id"])
                results.append({
                    **m,
                    "organization": orgs_by_id.get(oid, {"id": oid, "name": "Unknown Organization"}),
                })
            return results
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError(
                    "Phase 2 database tables ('organizations', 'organization_memberships') are not applied yet. "
                    "Execute supabase/migrations/20261125000001_phase2_enterprise_schema.sql in Supabase."
                ) from exc
            raise

    def list_members(self, organization_id: str) -> list[dict[str, Any]]:
        client = get_supabase_client()
        try:
            res = (
                client.table(self.MEMBERS_TABLE)
                .select("*")
                .eq("organization_id", organization_id)
                .order("created_at", desc=False)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError(
                    "Phase 2 database tables are not applied yet."
                ) from exc
            raise

    def add_or_update_member(
        self,
        organization_id: str,
        user_id: str,
        user_email: str,
        role: OrgRole,
        invited_by: str,
    ) -> dict[str, Any]:
        client = get_supabase_client()
        payload = {
            "organization_id": organization_id,
            "user_id": user_id,
            "user_email": user_email,
            "role": role.value,
            "status": "active",
            "invited_by": invited_by,
        }
        try:
            res = (
                client.table(self.MEMBERS_TABLE)
                .upsert(payload, on_conflict="organization_id,user_id")
                .execute()
            )
            return res.data[0] if res.data else payload
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 database tables are not applied yet.") from exc
            raise

    def update_member_role(
        self,
        organization_id: str,
        target_user_id: str,
        new_role: OrgRole,
    ) -> dict[str, Any] | None:
        client = get_supabase_client()
        try:
            # Guard against demoting the sole remaining Admin
            if new_role != OrgRole.ADMIN:
                admins = (
                    client.table(self.MEMBERS_TABLE)
                    .select("user_id")
                    .eq("organization_id", organization_id)
                    .eq("role", OrgRole.ADMIN.value)
                    .eq("status", "active")
                    .execute()
                ).data or []
                if len(admins) == 1 and str(admins[0]["user_id"]) == str(target_user_id):
                    raise ValueError("Cannot demote the last remaining Admin of the organization.")

            res = (
                client.table(self.MEMBERS_TABLE)
                .update({"role": new_role.value})
                .eq("organization_id", organization_id)
                .eq("user_id", target_user_id)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 database tables are not applied yet.") from exc
            raise

    def remove_member(self, organization_id: str, target_user_id: str) -> bool:
        client = get_supabase_client()
        try:
            admins = (
                client.table(self.MEMBERS_TABLE)
                .select("user_id")
                .eq("organization_id", organization_id)
                .eq("role", OrgRole.ADMIN.value)
                .eq("status", "active")
                .execute()
            ).data or []
            if len(admins) == 1 and str(admins[0]["user_id"]) == str(target_user_id):
                raise ValueError("Cannot remove the last remaining Admin of the organization.")

            res = (
                client.table(self.MEMBERS_TABLE)
                .delete()
                .eq("organization_id", organization_id)
                .eq("user_id", target_user_id)
                .execute()
            )
            return bool(res.data)
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 database tables are not applied yet.") from exc
            raise
