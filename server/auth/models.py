"""
RBAC and Authenticated Principal Models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrgRole(str, Enum):
    ADMIN = "Admin"
    COMPLIANCE_OFFICER = "Compliance Officer"
    CHA_BROKER = "CHA/Broker"
    VIEWER = "Viewer"


WRITER_ROLES: frozenset[OrgRole] = frozenset({
    OrgRole.ADMIN,
    OrgRole.COMPLIANCE_OFFICER,
    OrgRole.CHA_BROKER,
})

ALL_ROLES: frozenset[OrgRole] = frozenset({
    OrgRole.ADMIN,
    OrgRole.COMPLIANCE_OFFICER,
    OrgRole.CHA_BROKER,
    OrgRole.VIEWER,
})


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str
    full_name: str | None = None
    access_token: str = ""


@dataclass(frozen=True)
class OrganizationContext:
    user: AuthenticatedUser
    organization_id: str
    organization_name: str
    role: OrgRole
