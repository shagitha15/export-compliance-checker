"""
Pydantic Schemas for Authentication, Organization Management, and RBAC.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from server.auth.models import OrgRole


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, description="User email address")
    password: str = Field(..., min_length=8, description="Account password (min 8 chars)")
    full_name: Optional[str] = Field(default=None, description="Full name of user")
    organization_name: Optional[str] = Field(
        default=None,
        description="Optional initial organization to create with Admin role",
    )
    iec: Optional[str] = Field(default=None, description="Optional 10-digit DGFT IEC")
    gstin: Optional[str] = Field(default=None, description="Optional 15-character GSTIN")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class ResendConfirmationRequest(BaseModel):
    email: str = Field(..., min_length=5, description="Email address awaiting confirmation")


class ResendConfirmationResponse(BaseModel):
    success: bool = True
    message: str


class OrganizationInfo(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    iec: Optional[str] = None
    gstin: Optional[str] = None
    role: OrgRole
    status: str = "active"


class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: UserInfo
    organizations: list[OrganizationInfo] = Field(default_factory=list)
    schema_ready: bool = True
    single_user_mode: bool = False
    message: Optional[str] = None


class SignupResponse(BaseModel):
    user: UserInfo
    email_confirmation_required: bool = False
    session: Optional[AuthSessionResponse] = None
    organizations: list[OrganizationInfo] = Field(default_factory=list)
    schema_ready: bool = True
    single_user_mode: bool = False
    message: str


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    iec: Optional[str] = Field(default=None, max_length=20)
    gstin: Optional[str] = Field(default=None, max_length=20)


class MemberAddRequest(BaseModel):
    email: str = Field(..., min_length=5)
    role: OrgRole = Field(default=OrgRole.VIEWER)


class MemberRoleUpdateRequest(BaseModel):
    role: OrgRole


class MemberResponse(BaseModel):
    id: Optional[str] = None
    organization_id: str
    user_id: str
    user_email: Optional[str] = None
    role: OrgRole
    status: str = "active"
    created_at: Optional[Any] = None
