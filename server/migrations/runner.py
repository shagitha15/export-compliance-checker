"""
Supabase Schema Migration Runner & Live Verification Utility.
Applies SQL migrations when SUPABASE_DB_URL or SUPABASE_ACCESS_TOKEN is configured,
ensures private storage bucket provisioning, and verifies table presence honestly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from server.config.settings import get_settings
from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger

logger = get_logger("server.migrations")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"

REQUIRED_TABLES = [
    "organizations",
    "organization_memberships",
    "audit_batches",
    "batch_documents",
    "audit_findings",
    "compliance_reports",
]


def list_migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def check_schema_status() -> dict[str, Any]:
    """Probes Supabase PostgREST to report exact existence of each required Phase 2 table."""
    client = get_supabase_client()
    tables_status: dict[str, dict[str, Any]] = {}

    for table in REQUIRED_TABLES + ["customs_documents"]:
        try:
            res = client.table(table).select("id", count="exact").limit(0).execute()
            tables_status[table] = {"exists": True, "row_count": res.count}
        except Exception as exc:
            tables_status[table] = {"exists": False, "error": str(exc)}

    all_ready = all(tables_status[t]["exists"] for t in REQUIRED_TABLES)
    return {
        "phase2_schema_ready": all_ready,
        "tables": tables_status,
        "migration_files": [p.name for p in list_migration_files()],
    }


def ensure_private_storage_bucket(bucket_name: str | None = None) -> dict[str, Any]:
    """Creates or verifies the private Supabase Storage bucket for customs PDFs & reports."""
    settings = get_settings()
    target = bucket_name or settings.SUPABASE_STORAGE_BUCKET
    client = get_supabase_client()

    buckets = client.storage.list_buckets()
    existing = next((b for b in buckets if getattr(b, "name", None) == target or getattr(b, "id", None) == target), None)
    if existing:
        is_public = bool(getattr(existing, "public", False))
        if is_public:
            client.storage.update_bucket(target, options={"public": False})
        return {"bucket": target, "created": False, "public": False}

    client.storage.create_bucket(
        target,
        options={
            "public": False,
            "file_size_limit": settings.MAX_FILE_SIZE_BYTES,
            "allowed_mime_types": ["application/pdf"],
        },
    )
    logger.info("Provisioned private Supabase Storage bucket '%s'.", target)
    return {"bucket": target, "created": True, "public": False}


def apply_migrations() -> dict[str, Any]:
    """
    Attempts to apply SQL migration files via:
    1. SUPABASE_DB_URL (direct Postgres via psycopg / psycopg2 if installed)
    2. SUPABASE_ACCESS_TOKEN (Supabase Management API /v1/projects/{ref}/database/query)
    Never fabricates applied status if credentials are unavailable.
    """
    settings = get_settings()
    files = list_migration_files()
    if not files:
        return {"applied": False, "reason": "No migration SQL files found."}

    combined_sql = "\n\n".join(f.read_text(encoding="utf-8") for f in files)

    db_url = getattr(settings, "SUPABASE_DB_URL", None) or ""
    if db_url.strip():
        try:
            import psycopg  # type: ignore

            with psycopg.connect(db_url.strip(), autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(combined_sql)
            return {
                "applied": True,
                "method": "psycopg_direct",
                "files": [f.name for f in files],
                "schema_status": check_schema_status(),
            }
        except ImportError:
            pass

    access_token = getattr(settings, "SUPABASE_ACCESS_TOKEN", None) or ""
    if access_token.strip() and settings.SUPABASE_URL:
        host = urlparse(settings.SUPABASE_URL).hostname or ""
        project_ref = host.split(".")[0] if "." in host else ""
        if project_ref:
            url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token.strip()}",
                    "Content-Type": "application/json",
                },
                json={"query": combined_sql},
                timeout=30.0,
            )
            if resp.status_code in (200, 201):
                return {
                    "applied": True,
                    "method": "supabase_management_api",
                    "files": [f.name for f in files],
                    "schema_status": check_schema_status(),
                }
            return {
                "applied": False,
                "method": "supabase_management_api",
                "status_code": resp.status_code,
                "error": resp.text,
            }

    return {
        "applied": False,
        "method": "manual_sql_required",
        "reason": (
            "Neither SUPABASE_DB_URL nor SUPABASE_ACCESS_TOKEN is configured. "
            "Run supabase/migrations/20261125000001_phase2_enterprise_schema.sql in Supabase SQL Editor."
        ),
        "schema_status": check_schema_status(),
    }


if __name__ == "__main__":
    import json

    bucket_res = ensure_private_storage_bucket()
    mig_res = apply_migrations()
    print(json.dumps({"storage": bucket_res, "migrations": mig_res}, indent=2, default=str))
