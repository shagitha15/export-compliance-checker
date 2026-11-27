"""
Organization-Scoped Audit History & Private Storage Download Routes (v1).
Enforces strict organization isolation on all persisted batches, documents, and compliance PDFs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from server.auth.dependencies import require_org_context
from server.auth.models import OrganizationContext
from server.repositories.audit_repository import AuditRepository
from server.repositories.organization_repository import SchemaMigrationRequiredError
from server.storage.document_storage import DocumentStorageService

router = APIRouter(prefix="/audits", tags=["Audits & Reports"])


@router.get(
    "",
    summary="List Organization Audit Batches",
)
def list_organization_audits(
    limit: int = Query(default=25, ge=1, le=100),
    ctx: OrganizationContext = Depends(require_org_context()),
) -> dict:
    repo = AuditRepository()
    try:
        items = repo.list_batches(organization_id=ctx.organization_id, limit=limit)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {
        "organization_id": ctx.organization_id,
        "role": ctx.role.value,
        "audits": items,
    }


@router.get(
    "/{batch_id}",
    summary="Get Scoped Audit Batch Details",
)
def get_organization_audit_detail(
    batch_id: str,
    ctx: OrganizationContext = Depends(require_org_context()),
) -> dict:
    repo = AuditRepository()
    try:
        detail = repo.get_batch_detail(organization_id=ctx.organization_id, batch_external_id=batch_id)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit batch '{batch_id}' not found in your organization.",
        )
    return detail


@router.get(
    "/{batch_id}/documents/{doc_id}/signed-url",
    summary="Generate Signed URL for Private Uploaded Document PDF",
)
def get_document_signed_url(
    batch_id: str,
    doc_id: str,
    ctx: OrganizationContext = Depends(require_org_context()),
) -> dict:
    repo = AuditRepository()
    try:
        detail = repo.get_batch_detail(organization_id=ctx.organization_id, batch_external_id=batch_id)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit batch not found.")

    doc = next((d for d in detail["documents"] if str(d.get("id")) == str(doc_id)), None)
    if not doc or not doc.get("storage_path"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document storage object not found.")

    storage = DocumentStorageService()
    try:
        signed_url = storage.create_signed_download_url(
            organization_id=ctx.organization_id,
            storage_path=doc["storage_path"],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return {
        "batch_id": batch_id,
        "document_id": doc_id,
        "filename": doc.get("original_filename"),
        "signed_url": signed_url,
        "expires_in_seconds": storage.signed_ttl,
    }


@router.get(
    "/{batch_id}/report/signed-url",
    summary="Generate Signed URL for Private Compliance Report PDF",
)
def get_report_signed_url(
    batch_id: str,
    ctx: OrganizationContext = Depends(require_org_context()),
) -> dict:
    repo = AuditRepository()
    try:
        detail = repo.get_batch_detail(organization_id=ctx.organization_id, batch_external_id=batch_id)
    except SchemaMigrationRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not detail or not detail["reports"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance PDF report not found.")

    latest_report = detail["reports"][0]
    storage = DocumentStorageService()
    try:
        signed_url = storage.create_signed_download_url(
            organization_id=ctx.organization_id,
            storage_path=latest_report["storage_path"],
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return {
        "batch_id": batch_id,
        "report_filename": latest_report.get("report_filename"),
        "signed_url": signed_url,
        "expires_in_seconds": storage.signed_ttl,
    }
