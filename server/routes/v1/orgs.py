"""
Organization & RBAC Membership Management Routes (v1).
Supports Admin, Compliance Officer, CHA/Broker, and Viewer roles with strict tenant isolation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import get_current_user, require_org_context
from server.auth.models import AuthenticatedUser, OrganizationContext, OrgRole
from server.database.supabase import get_supabase_client
from server.repositories.organization_repository import (
    OrganizationRepository,
    SchemaMigrationRequiredError,
)
from server.schemas.auth import (
    CreateOrganizationRequest,
    MemberAddRequest,
    MemberResponse,
    MemberRoleUpdateRequest,
    OrganizationInfo,
)

router = APIRouter(prefix="/orgs", tags=["Organizations & RBAC"])


def _ensure_matching_org(org_id: str, ctx: OrganizationContext) -> None:
    if str(ctx.organization_id) != str(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: requested organization does not match authorized context.",
        )


@router.get(
    "",
    response_model=list[OrganizationInfo],
    summary="List Organizations Current User Belongs To",
)
def list_my_organizations(user: AuthenticatedUser = Depends(get_current_user)) -> list[OrganizationInfo]:
    repo = OrganizationRepository()
    try:
        rows = repo.list_user_organizations(user.user_id)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [
        OrganizationInfo(
            id=str(r["organization_id"]),
            name=str((r.get("organization") or {}).get("name") or "Organization"),
            slug=(r.get("organization") or {}).get("slug"),
            iec=(r.get("organization") or {}).get("iec"),
            gstin=(r.get("organization") or {}).get("gstin"),
            role=OrgRole(r["role"]),
            status=str(r.get("status") or "active"),
        )
        for r in rows
    ]


@router.post(
    "",
    response_model=OrganizationInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization (Creator Becomes Admin)",
)
def create_organization(
    payload: CreateOrganizationRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> OrganizationInfo:
    repo = OrganizationRepository()
    try:
        res = repo.create_organization(
            name=payload.name,
            creator_user_id=user.user_id,
            creator_email=user.email,
            iec=payload.iec,
            gstin=payload.gstin,
        )
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    org = res["organization"]
    return OrganizationInfo(
        id=str(org["id"]),
        name=str(org["name"]),
        slug=org.get("slug"),
        iec=org.get("iec"),
        gstin=org.get("gstin"),
        role=OrgRole.ADMIN,
        status="active",
    )


@router.get(
    "/{org_id}/members",
    response_model=list[MemberResponse],
    summary="List Members of Authorized Organization",
)
def list_org_members(
    org_id: str,
    ctx: OrganizationContext = Depends(require_org_context()),
) -> list[MemberResponse]:
    _ensure_matching_org(org_id, ctx)
    repo = OrganizationRepository()
    try:
        rows = repo.list_members(org_id)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return [
        MemberResponse(
            id=str(r.get("id")) if r.get("id") else None,
            organization_id=str(r["organization_id"]),
            user_id=str(r["user_id"]),
            user_email=r.get("user_email"),
            role=OrgRole(r["role"]),
            status=str(r.get("status") or "active"),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or Invite User to Organization (Admin Only)",
)
def add_org_member(
    org_id: str,
    payload: MemberAddRequest,
    ctx: OrganizationContext = Depends(require_org_context({OrgRole.ADMIN})),
) -> MemberResponse:
    _ensure_matching_org(org_id, ctx)
    target_email = payload.email.strip().lower()

    client = get_supabase_client()
    target_user_id: str | None = None
    try:
        users = client.auth.admin.list_users()
        for u in users:
            if (getattr(u, "email", None) or "").strip().lower() == target_email:
                target_user_id = str(u.id)
                break
        if not target_user_id:
            invited = client.auth.admin.invite_user_by_email(target_email)
            if invited and invited.user:
                target_user_id = str(invited.user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to look up or invite user '{target_email}': {str(exc)}",
        ) from exc

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find or invite Supabase user for email '{target_email}'.",
        )

    repo = OrganizationRepository()
    try:
        row = repo.add_or_update_member(
            organization_id=org_id,
            user_id=target_user_id,
            user_email=target_email,
            role=payload.role,
            invited_by=ctx.user.user_id,
        )
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return MemberResponse(
        id=str(row.get("id")) if row.get("id") else None,
        organization_id=str(row["organization_id"]),
        user_id=str(row["user_id"]),
        user_email=row.get("user_email"),
        role=OrgRole(row["role"]),
        status=str(row.get("status") or "active"),
        created_at=row.get("created_at"),
    )


@router.patch(
    "/{org_id}/members/{member_user_id}",
    response_model=MemberResponse,
    summary="Update Member Role (Admin Only)",
)
def update_org_member_role(
    org_id: str,
    member_user_id: str,
    payload: MemberRoleUpdateRequest,
    ctx: OrganizationContext = Depends(require_org_context({OrgRole.ADMIN})),
) -> MemberResponse:
    _ensure_matching_org(org_id, ctx)
    repo = OrganizationRepository()
    try:
        row = repo.update_member_role(org_id, member_user_id, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found.")

    return MemberResponse(
        id=str(row.get("id")) if row.get("id") else None,
        organization_id=str(row["organization_id"]),
        user_id=str(row["user_id"]),
        user_email=row.get("user_email"),
        role=OrgRole(row["role"]),
        status=str(row.get("status") or "active"),
        created_at=row.get("created_at"),
    )


@router.delete(
    "/{org_id}/members/{member_user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Member from Organization (Admin Only)",
)
def remove_org_member(
    org_id: str,
    member_user_id: str,
    ctx: OrganizationContext = Depends(require_org_context({OrgRole.ADMIN})),
) -> dict:
    _ensure_matching_org(org_id, ctx)
    repo = OrganizationRepository()
    try:
        removed = repo.remove_member(org_id, member_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in organization.")
    return {"success": True, "removed_user_id": member_user_id}
