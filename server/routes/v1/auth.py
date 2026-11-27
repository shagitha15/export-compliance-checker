"""
Authentication Routes (v1) powered by Supabase Auth.
Provides real user signup, login, token refresh, logout (revocation), and profile lookup.
Never exposes Supabase service-role secrets to clients.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from server.auth.dependencies import get_current_user
from server.auth.models import AuthenticatedUser, OrgRole
from server.config.settings import get_settings
from server.database.supabase import create_ephemeral_supabase_client, get_supabase_client
from server.logging.logger import get_logger
from server.repositories.organization_repository import (
    OrganizationRepository,
    SchemaMigrationRequiredError,
)
from server.schemas.auth import (
    AuthSessionResponse,
    LoginRequest,
    OrganizationInfo,
    RefreshTokenRequest,
    ResendConfirmationRequest,
    ResendConfirmationResponse,
    SignupRequest,
    SignupResponse,
    UserInfo,
)

logger = get_logger("server.routes.v1.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _is_email_not_confirmed_error(exc: Exception) -> bool:
    code = str(getattr(exc, "code", "") or "").strip().lower()
    message = str(exc).lower()
    return (
        code == "email_not_confirmed"
        or "email not confirmed" in message
        or "email_not_confirmed" in message
    )


def _is_single_user_mode() -> bool:
    return bool(getattr(get_settings(), "SINGLE_USER_MODE", False))


def _load_org_list(user_id: str) -> tuple[list[OrganizationInfo], bool]:
    repo = OrganizationRepository()
    try:
        rows = repo.list_user_organizations(user_id)
        orgs = [
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
        return orgs, True
    except SchemaMigrationRequiredError:
        return [], False


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User via Supabase Auth",
)
def signup(payload: SignupRequest) -> SignupResponse:
    auth_client = create_ephemeral_supabase_client()
    user_meta = {"full_name": payload.full_name} if payload.full_name else {}

    try:
        res = auth_client.auth.sign_up({
            "email": payload.email.strip(),
            "password": payload.password,
            "options": {"data": user_meta},
        })
    except Exception as exc:
        detail = str(exc)
        code = status.HTTP_400_BAD_REQUEST
        if "already registered" in detail.lower() or "already exists" in detail.lower():
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=f"Signup failed: {detail}") from exc

    if not res or not res.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase Auth did not return a created user record.",
        )

    uid = str(res.user.id)
    email = str(res.user.email or payload.email.strip())
    full_name = (getattr(res.user, "user_metadata", None) or {}).get("full_name") or payload.full_name
    user_info = UserInfo(user_id=uid, email=email, full_name=full_name)

    schema_ready = True
    if payload.organization_name:
        repo = OrganizationRepository()
        try:
            repo.create_organization(
                name=payload.organization_name,
                creator_user_id=uid,
                creator_email=email,
                iec=payload.iec,
                gstin=payload.gstin,
            )
        except SchemaMigrationRequiredError:
            schema_ready = False

    orgs, org_schema_ready = _load_org_list(uid)
    schema_ready = schema_ready and org_schema_ready

    single_user_mode = _is_single_user_mode()
    if res.session and res.session.access_token:
        session_resp = AuthSessionResponse(
            access_token=res.session.access_token,
            refresh_token=res.session.refresh_token or "",
            expires_in=int(getattr(res.session, "expires_in", 3600) or 3600),
            user=user_info,
            organizations=orgs,
            schema_ready=schema_ready,
            single_user_mode=single_user_mode,
            message=(
                None
                if (schema_ready or single_user_mode)
                else "Account created, but Phase 2 SQL schema migration must be applied for organizations."
            ),
        )
        return SignupResponse(
            user=user_info,
            email_confirmation_required=False,
            session=session_resp,
            organizations=orgs,
            schema_ready=schema_ready,
            single_user_mode=single_user_mode,
            message="User registered and signed in successfully.",
        )

    return SignupResponse(
        user=user_info,
        email_confirmation_required=True,
        session=None,
        organizations=orgs,
        schema_ready=schema_ready,
        single_user_mode=single_user_mode,
        message="Account created. Please confirm your email before signing in.",
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate User via Supabase Auth",
)
def login(payload: LoginRequest) -> AuthSessionResponse:
    auth_client = create_ephemeral_supabase_client()
    try:
        res = auth_client.auth.sign_in_with_password({
            "email": payload.email.strip(),
            "password": payload.password,
        })
    except Exception as exc:
        if _is_email_not_confirmed_error(exc):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": (
                        "Your email address has not been confirmed yet. Please check your inbox "
                        "for the verification link before signing in, or resend the confirmation email."
                    ),
                    "error_code": "email_not_confirmed",
                },
                headers={"X-Auth-Error-Code": "email_not_confirmed"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid email or password: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not res or not res.session or not res.user or not res.session.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: no active session issued.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = str(res.user.id)
    email = str(res.user.email or payload.email.strip())
    full_name = (getattr(res.user, "user_metadata", None) or {}).get("full_name")
    orgs, schema_ready = _load_org_list(uid)
    single_user_mode = _is_single_user_mode()

    return AuthSessionResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token or "",
        expires_in=int(getattr(res.session, "expires_in", 3600) or 3600),
        user=UserInfo(user_id=uid, email=email, full_name=full_name),
        organizations=orgs,
        schema_ready=schema_ready,
        single_user_mode=single_user_mode,
        message=(
            None
            if (schema_ready or single_user_mode)
            else "Signed in. Apply Phase 2 SQL migration to enable organizations & DB persistence."
        ),
    )


@router.post(
    "/resend-confirmation",
    response_model=ResendConfirmationResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend Signup Confirmation Email via Supabase Auth",
)
def resend_confirmation(payload: ResendConfirmationRequest) -> ResendConfirmationResponse:
    email = payload.email.strip()
    auth_client = create_ephemeral_supabase_client()
    try:
        auth_client.auth.resend({"type": "signup", "email": email})
    except Exception as exc:
        detail = str(exc) or "Unable to resend confirmation email."
        exc_status = int(getattr(exc, "status", 0) or 0)
        lower_detail = detail.lower()
        if (
            exc_status == 429
            or "rate limit" in lower_detail
            or "too many" in lower_detail
            or "security purposes" in lower_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait before requesting another confirmation email: {detail}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resend confirmation email: {detail}",
        ) from exc

    return ResendConfirmationResponse(
        success=True,
        message=f"Confirmation email sent to {email}. Please check your inbox and spam folder.",
    )


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Supabase Session Token",
)
def refresh_token(payload: RefreshTokenRequest) -> AuthSessionResponse:
    token_value = payload.refresh_token.strip()
    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer", "X-Auth-Error-Code": "refresh_failed"},
        )

    auth_client = create_ephemeral_supabase_client()
    try:
        res = auth_client.auth.refresh_session(token_value)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to refresh session: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer", "X-Auth-Error-Code": "refresh_failed"},
        ) from exc

    if not res or not res.session or not res.user or not res.session.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer", "X-Auth-Error-Code": "refresh_failed"},
        )

    uid = str(res.user.id)
    email = str(res.user.email or "")
    full_name = (getattr(res.user, "user_metadata", None) or {}).get("full_name")
    orgs, schema_ready = _load_org_list(uid)

    return AuthSessionResponse(
        access_token=res.session.access_token,
        refresh_token=res.session.refresh_token or token_value,
        expires_in=int(getattr(res.session, "expires_in", 3600) or 3600),
        user=UserInfo(user_id=uid, email=email, full_name=full_name),
        organizations=orgs,
        schema_ready=schema_ready,
        single_user_mode=_is_single_user_mode(),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke Active Supabase Session",
)
def logout(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    try:
        client = get_supabase_client()
        client.auth.admin.sign_out(user.access_token, scope="global")
    except Exception as exc:
        logger.warning("Supabase session revocation returned warning for user %s: %s", user.user_id, exc)
    return {"success": True, "message": "Session revoked successfully."}


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile & Organizations",
)
def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    orgs, schema_ready = _load_org_list(user.user_id)
    return {
        "user": UserInfo(user_id=user.user_id, email=user.email, full_name=user.full_name),
        "organizations": orgs,
        "schema_ready": schema_ready,
        "single_user_mode": _is_single_user_mode(),
    }
