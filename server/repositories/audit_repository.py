"""
Audit Repository for Organization-Scoped Persistence of Batches, Documents, Findings, and Reports.
"""

from __future__ import annotations

from typing import Any

from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger
from server.repositories.organization_repository import (
    SchemaMigrationRequiredError,
    _is_missing_table_error,
)

logger = get_logger("server.repositories.audit")


class AuditRepository:
    """Strictly scopes all queries and inserts by organization_id."""

    BATCHES_TABLE = "audit_batches"
    DOCS_TABLE = "batch_documents"
    FINDINGS_TABLE = "audit_findings"
    REPORTS_TABLE = "compliance_reports"

    def save_batch_audit(
        self,
        organization_id: str,
        user_id: str,
        batch_response_dict: dict[str, Any],
        document_storage_paths: dict[str, str] | None = None,
        document_hashes: dict[str, str] | None = None,
        overall_outcome: str | None = None,
    ) -> dict[str, Any]:
        client = get_supabase_client()
        summary = batch_response_dict.get("summary") or {}
        val = batch_response_dict.get("cross_document_validation")
        gov = batch_response_dict.get("government_compliance")
        storage_paths = document_storage_paths or {}
        hashes = document_hashes or {}

        derived_outcome = overall_outcome
        if not derived_outcome:
            if batch_response_dict.get("batch_status") == "FAILED" or (val and (val.get("summary") or {}).get("failed", 0) > 0):
                derived_outcome = "FAIL"
            elif batch_response_dict.get("batch_status") == "PARTIAL_SUCCESS" or summary.get("missing_document_types"):
                derived_outcome = "PARTIAL"
            else:
                derived_outcome = "PASS"

        batch_record = {
            "batch_id": batch_response_dict["batch_id"],
            "organization_id": organization_id,
            "created_by": user_id,
            "batch_status": batch_response_dict["batch_status"],
            "overall_outcome": derived_outcome,
            "total_files": summary.get("total_files_received", 0),
            "successful_files": summary.get("successful_count", 0),
            "failed_files": summary.get("failed_count", 0),
            "duplicate_files": summary.get("duplicate_count", 0),
            "summary": summary,
            "cross_document_validation": val,
            "government_compliance": gov,
        }

        try:
            batch_res = (
                client.table(self.BATCHES_TABLE)
                .upsert(batch_record, on_conflict="batch_id")
                .execute()
            )
            saved_batch = batch_res.data[0]
            batch_uuid = saved_batch["id"]

            # Save batch_documents rows
            docs_payload = []
            for doc in batch_response_dict.get("documents") or []:
                orig_name = doc.get("original_filename") or "document.pdf"
                saved_name = doc.get("saved_filename") or orig_name
                docs_payload.append({
                    "batch_id": batch_uuid,
                    "organization_id": organization_id,
                    "uploaded_by": user_id,
                    "original_filename": orig_name,
                    "saved_filename": doc.get("saved_filename"),
                    "storage_path": storage_paths.get(saved_name) or storage_paths.get(orig_name),
                    "sha256_hash": hashes.get(saved_name) or hashes.get(orig_name),
                    "file_size_bytes": doc.get("file_size_bytes", 0),
                    "document_type": doc.get("document_type"),
                    "processing_status": doc.get("status", "SUCCESS"),
                    "extraction_method": doc.get("extraction_method"),
                    "fallback_used": bool(doc.get("fallback_used")),
                    "warning": doc.get("warning"),
                    "error_code": doc.get("error_code"),
                    "error_message": doc.get("error"),
                    "extracted_data": doc.get("extracted_data"),
                })

            if docs_payload:
                client.table(self.DOCS_TABLE).insert(docs_payload).execute()

            # Save audit_findings rows (Stage 1, Stage 2, Statutory)
            findings_payload: list[dict[str, Any]] = []
            if val:
                for intra in val.get("intra_document_results") or []:
                    findings_payload.append({
                        "batch_id": batch_uuid,
                        "organization_id": organization_id,
                        "stage": "INTRA_DOCUMENT",
                        "rule_id": intra.get("check_id") or intra.get("check_name") or "INTRA",
                        "rule_name": intra.get("rule_name") or intra.get("check_name") or "Intra Check",
                        "document_type": intra.get("document_type"),
                        "field_name": intra.get("check_name"),
                        "status": intra.get("status", "PASS"),
                        "message": intra.get("message") or intra.get("discrepancy"),
                    })
                for cross in val.get("cross_document_results") or []:
                    findings_payload.append({
                        "batch_id": batch_uuid,
                        "organization_id": organization_id,
                        "stage": "CROSS_DOCUMENT",
                        "rule_id": cross.get("check_id", "XDOC"),
                        "rule_name": cross.get("rule_name", "Cross-Document Check"),
                        "document_type": ", ".join(cross.get("documents_involved") or []),
                        "field_name": cross.get("field_name"),
                        "status": cross.get("status", "PASS"),
                        "expected_value": str(cross.get("expected_value")) if cross.get("expected_value") is not None else None,
                        "observed_value": cross.get("observed_values"),
                        "message": cross.get("message") or (str(cross.get("discrepancy")) if cross.get("discrepancy") else None),
                    })
            if gov:
                for f in gov.get("findings") or []:
                    findings_payload.append({
                        "batch_id": batch_uuid,
                        "organization_id": organization_id,
                        "stage": "STATUTORY",
                        "rule_id": f.get("rule_id", "STAT"),
                        "rule_name": f.get("rule_title", "Statutory Rule"),
                        "authority": f.get("authority"),
                        "status": f.get("status", "ADVISORY"),
                        "message": f.get("observed_evidence"),
                        "remediation": f.get("action_required"),
                    })

            if findings_payload:
                client.table(self.FINDINGS_TABLE).insert(findings_payload).execute()

            return saved_batch
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError(
                    "Phase 2 audit tables are not applied yet in Supabase."
                ) from exc
            raise

    def save_compliance_report(
        self,
        organization_id: str,
        batch_external_id: str,
        generated_by: str,
        report_filename: str,
        storage_path: str,
        file_size_bytes: int,
        overall_outcome: str | None = None,
    ) -> dict[str, Any] | None:
        client = get_supabase_client()
        try:
            batch_row = (
                client.table(self.BATCHES_TABLE)
                .select("id")
                .eq("organization_id", organization_id)
                .eq("batch_id", batch_external_id)
                .limit(1)
                .execute()
            ).data
            if not batch_row:
                return None

            payload = {
                "batch_id": batch_row[0]["id"],
                "organization_id": organization_id,
                "generated_by": generated_by,
                "report_filename": report_filename,
                "storage_path": storage_path,
                "file_size_bytes": file_size_bytes,
                "overall_outcome": overall_outcome,
            }
            res = client.table(self.REPORTS_TABLE).insert(payload).execute()
            return res.data[0] if res.data else payload
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 report tables are not applied yet.") from exc
            raise

    def list_batches(self, organization_id: str, limit: int = 25) -> list[dict[str, Any]]:
        client = get_supabase_client()
        try:
            res = (
                client.table(self.BATCHES_TABLE)
                .select("id,batch_id,organization_id,created_by,shipment_ref,batch_status,overall_outcome,compliance_score,authenticity_score,total_files,successful_files,failed_files,duplicate_files,summary,created_at,updated_at")
                .eq("organization_id", organization_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 audit tables are not applied yet.") from exc
            raise

    def get_batch_detail(self, organization_id: str, batch_external_id: str) -> dict[str, Any] | None:
        client = get_supabase_client()
        try:
            batch_res = (
                client.table(self.BATCHES_TABLE)
                .select("*")
                .eq("organization_id", organization_id)
                .eq("batch_id", batch_external_id)
                .limit(1)
                .execute()
            ).data
            if not batch_res:
                return None

            batch = batch_res[0]
            batch_uuid = batch["id"]

            docs = (
                client.table(self.DOCS_TABLE)
                .select("*")
                .eq("organization_id", organization_id)
                .eq("batch_id", batch_uuid)
                .execute()
            ).data or []

            findings = (
                client.table(self.FINDINGS_TABLE)
                .select("*")
                .eq("organization_id", organization_id)
                .eq("batch_id", batch_uuid)
                .execute()
            ).data or []

            reports = (
                client.table(self.REPORTS_TABLE)
                .select("*")
                .eq("organization_id", organization_id)
                .eq("batch_id", batch_uuid)
                .order("created_at", desc=True)
                .execute()
            ).data or []

            return {
                "batch": batch,
                "documents": docs,
                "findings": findings,
                "reports": reports,
            }
        except Exception as exc:
            if _is_missing_table_error(exc):
                raise SchemaMigrationRequiredError("Phase 2 audit tables are not applied yet.") from exc
            raise
