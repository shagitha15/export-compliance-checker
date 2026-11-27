"""
FastAPI Security Dependencies for Authentication, Organization Isolation, and RBAC.
"""

from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.auth.jwt_verifier import verify_supabase_jwt
from server.auth.models import ALL_ROLES, AuthenticatedUser, OrganizationContext, OrgRole
from server.config.settings import get_settings
from server.repositories.organization_repository import (
    OrganizationRepository,
    SchemaMigrationRequiredError,
)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """Enforces Bearer JWT authentication on protected endpoints."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer JWT token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Expected Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_supabase_jwt(credentials.credentials)


def require_org_context(
    allowed_roles: Iterable[OrgRole] | None = None,
) -> Callable[..., OrganizationContext]:
    """
    FastAPI dependency factory that:
    1. Verifies JWT authentication.
    2. Resolves target organization from X-Organization-ID header (or query param, or sole active membership).
    3. Enforces active membership in that organization (403 Forbidden otherwise).
    4. Enforces RBAC role membership against `allowed_roles`.
    """
    permitted = frozenset(allowed_roles) if allowed_roles is not None else ALL_ROLES

    def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),
        x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
        organization_id: str | None = Query(default=None),
    ) -> OrganizationContext:
        requested_org_id = (x_organization_id or organization_id or "").strip() or None
        repo = OrganizationRepository()

        try:
            memberships = repo.list_user_organizations(user.user_id)
        except SchemaMigrationRequiredError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        active_memberships = [m for m in memberships if m.get("status") == "active"]

        if requested_org_id:
            match = next(
                (m for m in active_memberships if str(m.get("organization_id")) == requested_org_id),
                None,
            )
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not belong to the requested organization.",
                )
        else:
            if len(active_memberships) == 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No active organization membership found. Create or join an organization first.",
                )
            if len(active_memberships) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Multiple organizations found. Specify X-Organization-ID header.",
                )
            match = active_memberships[0]

        try:
            role = OrgRole(match["role"])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid organization role '{match.get('role')}'.",
            ) from exc

        if role not in permitted:
            allowed_labels = ", ".join(sorted(r.value for r in permitted))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for role '{role.value}'. Required: {allowed_labels}.",
            )

        org_info = match.get("organization") or {}
        return OrganizationContext(
            user=user,
            organization_id=str(match["organization_id"]),
            organization_name=str(org_info.get("name") or "Organization"),
            role=role,
        )

    return _dependency


def require_roles(*roles: OrgRole) -> Callable[..., OrganizationContext]:
    """Convenience alias for `require_org_context(allowed_roles=roles)`."""
    return require_org_context(allowed_roles=roles)


def require_workflow_context(
    allowed_roles: Iterable[OrgRole] | None = None,
) -> Callable[..., OrganizationContext | None]:
    """
    Document-workflow authorization dependency.

    - Always requires a valid Supabase JWT via `get_current_user`.
    - When `SINGLE_USER_MODE` is enabled, bypasses organization membership and RBAC
      checks for the document workflow and returns `None` (leaving Phase 2 tables unused).
    - When `SINGLE_USER_MODE` is disabled (default), enforces strict organization
      isolation and RBAC via `require_org_context`.
    """
    permitted = frozenset(allowed_roles) if allowed_roles is not None else ALL_ROLES
    strict_dependency = require_org_context(allowed_roles=permitted)

    def _dependency(
        user: AuthenticatedUser = Depends(get_current_user),
        x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
        organization_id: str | None = Query(default=None),
    ) -> OrganizationContext | None:
        settings = get_settings()
        if bool(getattr(settings, "SINGLE_USER_MODE", False)):
            return None
        return strict_dependency(
            user=user,
            x_organization_id=x_organization_id,
            organization_id=organization_id,
        )

    return _dependency
