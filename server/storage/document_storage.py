"""
Secure Private Document Storage Service backed by Supabase Storage (`customs-documents` bucket).
Enforces organization-prefixed paths (`<organization_id>/<batch_id>/<filename>`)
and issues short-lived signed URLs after backend RBAC/org authorization.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.config.settings import get_settings
from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger

logger = get_logger("server.storage.documents")


def _safe_segment(val: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._\-]", "_", (val or "").strip()).strip("._")
    return cleaned or fallback


def build_org_storage_path(organization_id: str, batch_id: str, filename: str) -> str:
    """Builds a strict org-scoped storage object key preventing path traversal."""
    org_seg = _safe_segment(organization_id, "org")
    batch_seg = _safe_segment(batch_id, "batch")
    file_seg = _safe_segment(Path(filename).name, "document.pdf")
    return f"{org_seg}/{batch_seg}/{file_seg}"


class DocumentStorageService:
    """Manages private PDF uploads, downloads, and short-lived signed URLs."""

    def __init__(self, bucket_name: str | None = None) -> None:
        settings = get_settings()
        self.bucket = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "customs-documents"
        self.signed_ttl = int(getattr(settings, "SIGNED_URL_TTL_SECONDS", 300))

    def upload_private_pdf(
        self,
        organization_id: str,
        batch_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        if not organization_id:
            raise ValueError("organization_id is required for private document storage.")
        if not content:
            raise ValueError("Cannot upload empty file bytes to storage.")

        storage_path = build_org_storage_path(organization_id, batch_id, filename)
        client = get_supabase_client()
        client.storage.from_(self.bucket).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        logger.info("Uploaded private PDF to bucket '%s' at '%s'.", self.bucket, storage_path)
        return storage_path

    def create_signed_download_url(
        self,
        organization_id: str,
        storage_path: str,
        expires_in: int | None = None,
    ) -> str:
        if not storage_path or not storage_path.startswith(f"{_safe_segment(organization_id)}/"):
            raise PermissionError("Storage path does not belong to the authenticated organization.")

        ttl = expires_in or self.signed_ttl
        client = get_supabase_client()
        res = client.storage.from_(self.bucket).create_signed_url(storage_path, ttl)
        signed = res.get("signedURL") or res.get("signedUrl") if isinstance(res, dict) else None
        if not signed:
            raise RuntimeError(f"Failed to generate signed URL for '{storage_path}'.")
        return signed

    def download_private_pdf(self, organization_id: str, storage_path: str) -> bytes:
        if not storage_path or not storage_path.startswith(f"{_safe_segment(organization_id)}/"):
            raise PermissionError("Storage path does not belong to the authenticated organization.")

        client = get_supabase_client()
        return client.storage.from_(self.bucket).download(storage_path)
