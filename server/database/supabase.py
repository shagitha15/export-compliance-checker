"""
Supabase PostgreSQL, Auth, and Storage Client Connection Manager.
Uses HTTP/1.1 transport to prevent Windows HTTP/2 connection resets (WinError 10054)
and isolates per-request user auth operations from the backend service client.
"""

from __future__ import annotations

import httpx
from supabase import Client, ClientOptions, create_client
from server.config.settings import get_settings
from server.logging.logger import get_logger

logger = get_logger("server.database.supabase")

# Cached singleton service/backend client instance
_supabase_client: Client | None = None


def _build_client_options() -> ClientOptions:
    transport = httpx.HTTPTransport(http2=False, retries=2)
    http_client = httpx.Client(http2=False, transport=transport, timeout=20.0)
    return ClientOptions(httpx_client=http_client, persist_session=False, auto_refresh_token=False)


def _validate_supabase_settings() -> tuple[str, str]:
    settings = get_settings()
    supabase_url = settings.SUPABASE_URL
    supabase_key = settings.SUPABASE_KEY

    if not supabase_url or supabase_url.strip() in (
        "",
        "your_supabase_url_here",
        "your_supabase_project_url_here",
    ):
        raise ValueError(
            "SUPABASE_URL is not configured in environment settings. "
            "Please configure your project URL (e.g. https://your-project.supabase.co)."
        )

    if not supabase_key or supabase_key.strip() in (
        "",
        "your_supabase_key_here",
        "your_supabase_api_key_here",
    ):
        raise ValueError(
            "SUPABASE_KEY is not configured in environment settings. "
            "Please provide your Supabase service-role/secret API key."
        )

    return supabase_url.strip(), supabase_key.strip()


def get_supabase_client(force_new: bool = False) -> Client:
    """
    Returns the singleton backend Supabase client configured with HTTP/1.1 + retries.
    Never calls user sign-in on this instance so backend credentials remain intact.
    """
    global _supabase_client

    if _supabase_client is not None and not force_new:
        return _supabase_client

    supabase_url, supabase_key = _validate_supabase_settings()

    try:
        _supabase_client = create_client(supabase_url, supabase_key, options=_build_client_options())
        logger.info("Supabase client initialized successfully for URL: %s", supabase_url)
        return _supabase_client
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc)
        raise RuntimeError(f"Could not connect to Supabase: {str(exc)}") from exc


def create_ephemeral_supabase_client() -> Client:
    """
    Creates an isolated, short-lived Supabase client for user login/signup/refresh
    so user session mutations never alter the shared service client headers.
    """
    supabase_url, supabase_key = _validate_supabase_settings()
    settings = get_settings()
    auth_key = (settings.SUPABASE_ANON_KEY or "").strip() or supabase_key
    return create_client(supabase_url, auth_key, options=_build_client_options())
