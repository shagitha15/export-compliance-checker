"""
Supabase JWT Verification Module.
Verifies JWT signatures using Supabase JWKS (ES256/RS256) or HS256 secret,
validates standard claims (exp, aud, sub), and checks session revocation via Supabase Auth.
"""

from __future__ import annotations

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient

from server.auth.models import AuthenticatedUser
from server.config.settings import get_settings
from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger

logger = get_logger("server.auth.jwt")

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _decode_jwt_claims(token: str) -> dict:
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        alg = (header.get("alg") or "ES256").upper()
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        if alg == "HS256":
            secret = (getattr(settings, "SUPABASE_JWT_SECRET", "") or "").strip()
            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="HS256 JWT secret is not configured for signature verification.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                leeway=30,
            )

        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            leeway=30,
        )
    except HTTPException:
        raise
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired JWT token: {exc}",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"',
                "X-Auth-Error-Code": "token_expired",
            },
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired JWT token: {exc}",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token"',
                "X-Auth-Error-Code": "invalid_token",
            },
        ) from exc
    except Exception as exc:
        logger.warning("JWKS verification error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify token signature against Supabase JWKS.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def verify_supabase_jwt(token: str, check_revocation: bool = True) -> AuthenticatedUser:
    """
    Validates a Supabase JWT Bearer token and returns the authenticated user principal.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clean_token = token.strip()
    claims = _decode_jwt_claims(clean_token)

    user_id = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip()
    user_meta = claims.get("user_metadata") or {}
    full_name = user_meta.get("full_name") if isinstance(user_meta, dict) else None

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token missing subject ('sub') claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if check_revocation:
        try:
            client = get_supabase_client()
            resp = client.auth.get_user(clean_token)
            if not resp or not resp.user or str(resp.user.id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session is invalid or has been logged out.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            email = resp.user.email or email
            meta = getattr(resp.user, "user_metadata", None) or {}
            if isinstance(meta, dict) and meta.get("full_name"):
                full_name = meta.get("full_name")
        except HTTPException:
            raise
        except (httpx.HTTPError, OSError) as net_exc:
            # Cryptographic JWKS verification already succeeded; fail open only on transient network IO
            logger.debug("Supabase get_user revocation check skipped due to network IO: %s", net_exc)
        except Exception as exc:
            err_msg = str(exc).lower()
            if "session" in err_msg or "invalid" in err_msg or "expired" in err_msg or "jwt" in err_msg or "401" in err_msg or "403" in err_msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication session expired or revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from exc
            logger.debug("Non-fatal revocation check error after JWKS verification: %s", exc)

    return AuthenticatedUser(
        user_id=user_id,
        email=email,
        full_name=full_name,
        access_token=clean_token,
    )
